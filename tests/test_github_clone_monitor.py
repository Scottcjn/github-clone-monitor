import json

import github_clone_monitor as monitor


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def day(stamp, count, uniques):
    return {"timestamp": f"{stamp}T00:00:00Z", "count": count, "uniques": uniques}


def stats(count, uniques, days):
    """The shape get_clone_stats returns for a 200 response."""
    return {
        "count": count,
        "uniques": uniques,
        "days": {d["timestamp"]: {"count": d["count"], "uniques": d["uniques"]}
                 for d in days},
    }


def test_get_clone_stats_returns_normalized_counts(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse(200, {
            "count": 12,
            "uniques": 5,
            "clones": [day("2026-07-28", 4, 2), day("2026-07-29", 8, 3)],
        })

    monkeypatch.setattr(monitor, "GITHUB_USERNAME", "octocat")
    monkeypatch.setattr(monitor, "GITHUB_TOKEN", "token-123")
    monkeypatch.setattr(monitor.requests, "get", fake_get)

    assert monitor.get_clone_stats("demo") == stats(
        12, 5, [day("2026-07-28", 4, 2), day("2026-07-29", 8, 3)]
    )
    assert captured == {
        "url": "https://api.github.com/repos/octocat/demo/traffic/clones",
        "headers": {"Authorization": "token token-123"},
        "timeout": 10,
    }


def test_get_clone_stats_keeps_the_per_day_breakdown(monkeypatch):
    """The window total alone cannot detect new clones, so the days must survive."""
    monkeypatch.setattr(
        monitor.requests, "get",
        lambda url, headers, timeout: DummyResponse(200, {
            "count": 31, "uniques": 20,
            "clones": [day("2026-07-15", 25, 15), day("2026-07-28", 6, 5)],
        }),
    )

    result = monitor.get_clone_stats("demo")

    assert result["days"] == {
        "2026-07-15T00:00:00Z": {"count": 25, "uniques": 15},
        "2026-07-28T00:00:00Z": {"count": 6, "uniques": 5},
    }


def test_get_clone_stats_returns_none_for_auth_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        monitor.requests,
        "get",
        lambda url, headers, timeout: DummyResponse(401),
    )

    assert monitor.get_clone_stats("private-repo") is None
    assert "Bad token" in capsys.readouterr().out


def test_get_clone_stats_reports_rate_limiting(monkeypatch, capsys):
    monkeypatch.setattr(
        monitor.requests,
        "get",
        lambda url, headers, timeout: DummyResponse(403),
    )

    assert monitor.get_clone_stats("busy-repo") is None
    assert "Rate limited" in capsys.readouterr().out


def test_state_round_trip_uses_configured_state_file(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))

    assert monitor.load_state() == {}

    monitor.save_state({"repo": {"count": 4, "uniques": 2}})

    assert json.loads(state_file.read_text()) == {"repo": {"count": 4, "uniques": 2}}
    assert monitor.load_state() == {"repo": {"count": 4, "uniques": 2}}


def test_new_clones_counts_each_day_on_its_own():
    before = stats(7, 5, [day("2026-07-28", 7, 5)])
    after = stats(10, 7, [day("2026-07-28", 7, 5), day("2026-07-29", 3, 2)])

    assert monitor.new_clones_since(before, after) == (3, 2)


def test_new_clones_ignores_days_that_left_the_window():
    """A busy day ageing out drops the 14-day total; that is not negative activity."""
    before = stats(31, 20, [day("2026-07-15", 25, 15), day("2026-07-28", 6, 5)])
    after = stats(15, 12, [day("2026-07-28", 6, 5), day("2026-07-29", 9, 7)])

    # The window total fell by 16 even though 9 real clones arrived.
    assert after["count"] < before["count"]
    assert monitor.new_clones_since(before, after) == (9, 7)


def test_new_clones_never_goes_negative_when_a_day_is_restated():
    before = stats(10, 6, [day("2026-07-29", 10, 6)])
    after = stats(8, 5, [day("2026-07-29", 8, 5)])

    assert monitor.new_clones_since(before, after) == (0, 0)


def test_check_repos_alerts_only_on_new_clones(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "alpha": stats(2, 2, [day("2026-07-28", 2, 2)]),
        "beta": stats(7, 4, [day("2026-07-28", 7, 4)]),
    }))
    alerts = []

    current = {
        "alpha": stats(5, 3, [day("2026-07-28", 2, 2), day("2026-07-29", 3, 1)]),
        "beta": stats(7, 4, [day("2026-07-28", 7, 4)]),
        "gamma": stats(1, 1, [day("2026-07-29", 1, 1)]),
    }

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha", "beta", "gamma"])
    monkeypatch.setattr(monitor, "get_clone_stats", lambda repo: current[repo])
    monkeypatch.setattr(monitor, "alert", alerts.append)

    assert monitor.check_repos() == 3
    assert alerts == [
        "alpha: +3 new clones (1 unique)! They're onto you! (14-day total: 5)"
    ]
    assert monitor.load_state() == current


def test_check_repos_alerts_when_the_window_total_falls(tmp_path, monkeypatch):
    """The regression: an expiring busy day used to hide every new clone."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "alpha": stats(31, 20, [day("2026-07-15", 25, 15), day("2026-07-28", 6, 5)]),
    }))
    alerts = []

    after = stats(15, 12, [day("2026-07-28", 6, 5), day("2026-07-29", 9, 7)])

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha"])
    monkeypatch.setattr(monitor, "get_clone_stats", lambda repo: after)
    monkeypatch.setattr(monitor, "alert", alerts.append)

    assert monitor.check_repos() == 9
    assert alerts == [
        "alpha: +9 new clones (7 unique)! They're onto you! (14-day total: 15)"
    ]


def test_failed_fetch_keeps_the_previous_baseline(tmp_path, monkeypatch, capsys):
    """A 403 or a timeout must not wipe what we already knew about a repo."""
    state_file = tmp_path / "state.json"
    known = stats(2, 2, [day("2026-07-28", 2, 2)])
    state_file.write_text(json.dumps({"alpha": known}))

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha"])
    monkeypatch.setattr(monitor, "get_clone_stats", lambda repo: None)
    monkeypatch.setattr(monitor, "alert", lambda message: None)

    assert monitor.check_repos() == 0
    assert monitor.load_state() == {"alpha": known}
    assert "baseline kept" in capsys.readouterr().out


def test_alert_still_fires_on_the_sweep_after_a_failure(tmp_path, monkeypatch):
    """Without the baseline the next sweep reads as a first sweep and stays silent."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"alpha": stats(2, 2, [day("2026-07-28", 2, 2)])}))
    alerts = []
    responses = iter([
        None,
        stats(6, 5, [day("2026-07-28", 2, 2), day("2026-07-29", 4, 3)]),
    ])

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha"])
    monkeypatch.setattr(monitor, "get_clone_stats", lambda repo: next(responses))
    monkeypatch.setattr(monitor, "alert", alerts.append)

    monitor.check_repos()          # the sweep that failed
    assert monitor.check_repos() == 4

    assert alerts == [
        "alpha: +4 new clones (3 unique)! They're onto you! (14-day total: 6)"
    ]


def test_state_from_an_older_version_rebaselines_without_alerting(tmp_path, monkeypatch, capsys):
    """Old state has no per-day detail; inventing a diff from it would cry wolf."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"alpha": {"count": 2, "uniques": 2}}))
    alerts = []

    after = stats(9, 7, [day("2026-07-28", 2, 2), day("2026-07-29", 7, 5)])

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha"])
    monkeypatch.setattr(monitor, "get_clone_stats", lambda repo: after)
    monkeypatch.setattr(monitor, "alert", alerts.append)

    assert monitor.check_repos() == 0
    assert alerts == []
    assert "baseline rebuilt" in capsys.readouterr().out
    assert monitor.load_state() == {"alpha": after}


def test_alert_runs_notify_send_without_a_shell(monkeypatch, capsys):
    """The alert message must never be interpolated into a shell string.

    The message contains the repo name, which is attacker-influenced (it is
    derived from the repo list / GitHub API). If it were run through a shell a
    message like `repo" ; touch /tmp/pwned ; echo "` would execute an arbitrary
    command. subprocess.run with a list argument passes the message as a single
    argv element, so nothing can be interpreted as shell syntax.
    """
    calls = []

    def fake_run(args, timeout, check, stdout, stderr):
        calls.append({"args": args, "timeout": timeout, "check": check})
        return object()

    monkeypatch.setattr(monitor.subprocess, "run", fake_run)

    hostile_message = 'unsafe" ; touch /tmp/pwned_glowie ; echo "'
    monitor.alert(hostile_message)

    assert len(calls) == 1
    argv = calls[0]["args"]
    assert argv[0] == "notify-send"
    # The whole hostile string survives as ONE argument; no shell split it.
    assert argv[-1] == hostile_message
    assert calls[0]["timeout"] == 5
    assert calls[0]["check"] is False
    # The injected command was never executed.
    import os
    assert not os.path.exists("/tmp/pwned_glowie")


def test_alert_swallows_missing_notify_send(monkeypatch, capsys):
    """alert() must not crash when notify-send is absent (headless boxes)."""
    def boom(*a, **k):
        raise FileNotFoundError
    monkeypatch.setattr(monitor.subprocess, "run", boom)
    # Should not raise
    monitor.alert("quiet host")
    out = capsys.readouterr().out
    assert "GLOWIE ALERT" in out  # terminal message still printed
