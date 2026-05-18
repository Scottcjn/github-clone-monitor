import json

import github_clone_monitor as monitor


class DummyResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_get_clone_stats_returns_normalized_counts(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse(200, {"count": 12, "uniques": 5})

    monkeypatch.setattr(monitor, "GITHUB_USERNAME", "octocat")
    monkeypatch.setattr(monitor, "GITHUB_TOKEN", "token-123")
    monkeypatch.setattr(monitor.requests, "get", fake_get)

    assert monitor.get_clone_stats("demo") == {"count": 12, "uniques": 5}
    assert captured == {
        "url": "https://api.github.com/repos/octocat/demo/traffic/clones",
        "headers": {"Authorization": "token token-123"},
        "timeout": 10,
    }


def test_get_clone_stats_returns_none_for_auth_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        monitor.requests,
        "get",
        lambda url, headers, timeout: DummyResponse(401),
    )

    assert monitor.get_clone_stats("private-repo") is None
    assert "Bad token" in capsys.readouterr().out


def test_state_round_trip_uses_configured_state_file(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))

    assert monitor.load_state() == {}

    monitor.save_state({"repo": {"count": 4, "uniques": 2}})

    assert json.loads(state_file.read_text()) == {"repo": {"count": 4, "uniques": 2}}
    assert monitor.load_state() == {"repo": {"count": 4, "uniques": 2}}


def test_check_repos_alerts_only_on_new_clones(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"alpha": {"count": 2}, "beta": {"count": 7}}))
    alerts = []

    monkeypatch.setattr(monitor, "STATE_FILE", str(state_file))
    monkeypatch.setattr(monitor, "REPOS", ["alpha", "beta", "gamma"])
    monkeypatch.setattr(
        monitor,
        "get_clone_stats",
        lambda repo: {
            "alpha": {"count": 5, "uniques": 3},
            "beta": {"count": 7, "uniques": 4},
            "gamma": {"count": 1, "uniques": 1},
        }[repo],
    )
    monkeypatch.setattr(monitor, "alert", alerts.append)

    assert monitor.check_repos() == 3
    assert alerts == ["alpha: +3 new clones! They're onto you! (Total: 5)"]
    assert monitor.load_state() == {
        "alpha": {"count": 5, "uniques": 3},
        "beta": {"count": 7, "uniques": 4},
        "gamma": {"count": 1, "uniques": 1},
    }
