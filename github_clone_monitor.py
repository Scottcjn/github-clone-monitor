#!/usr/bin/env python3
"""
GitHub Clone Monitor - Watch the Watchers
Built on Christmas Day 2025 when the glowies came for my repos

"436 clones in 48 hours. Zero stars. The glowies don't leave reviews."
"""

import json
import os
import time
import requests
from datetime import datetime

# Configuration - GET YOUR OWN TOKEN, GLOWIE
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "your_token_here")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "Scottcjn")
REPOS = [
    "rust-ppc-tiger",
    "ppc-tiger-tools", 
    "exo",
    "Rustchain",
    "claude-code-g4",
    "llama-cpp-tigerleopard",
    "ppc-compilers",
    "llama-cpp-power8",
    "claude-code-monterey",
]
CHECK_INTERVAL = 300  # 5 minutes - fast enough to catch them in the act
STATE_FILE = os.path.expanduser("~/.github_clone_state.json")

def get_clone_stats(repo):
    """Fetch clone stats - see who's watching"""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo}/traffic/clones"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {"count": data["count"], "uniques": data["uniques"]}
        elif resp.status_code == 401:
            print("  [!] Bad token - the glowies changed your password?")
    except Exception as e:
        print(f"  [!] Error fetching {repo}: {e}")
    return None

def load_state():
    """Load previous state - remember who was here before"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Save current state - evidence for later"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def alert(message):
    """ALERT! The glowies are here!"""
    print(f"\n{'='*60}")
    print(f"  GLOWIE ALERT: {message}")
    print(f"{'='*60}\n")

    # Desktop notification (Linux)
    try:
        os.system(f'notify-send "GLOWIE ALERT" "{message}" 2>/dev/null')
    except:
        pass

    # Terminal bell - wake up!
    print('\a')

def check_repos():
    """Check all repos - are they watching?"""
    state = load_state()
    new_state = {}
    total_new_clones = 0

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Scanning for glowie activity...")

    for repo in REPOS:
        stats = get_clone_stats(repo)
        if stats:
            new_state[repo] = stats

            if repo in state:
                old_count = state[repo]["count"]
                new_count = stats["count"]
                diff = new_count - old_count

                if diff > 0:
                    total_new_clones += diff
                    alert(f"{repo}: +{diff} new clones! They're onto you! (Total: {new_count})")
                else:
                    print(f"  {repo}: {new_count} clones (quiet... too quiet)")
            else:
                print(f"  {repo}: {stats['count']} clones ({stats['uniques']} unique) [first sweep]")

    save_state(new_state)

    if total_new_clones > 0:
        print(f"\n  TOTAL GLOWIE CLONES: +{total_new_clones}")
        print(f"  They're not even trying to hide anymore.")

    return total_new_clones

def main():
    print(r"""
    ╔═══════════════════════════════════════════════════════════╗
    ║         GITHUB CLONE MONITOR - GLOWIE EDITION             ║
    ║                                                           ║
    ║   "436 clones in 48 hours. Zero stars. Zero forks.        ║
    ║    No referrers. Just... watching."                       ║
    ║                                                           ║
    ║   The PowerPC G4 was classified as a WEAPON in 1999.      ║
    ║   Now someone's cloning your G4 compiler repos.           ║
    ║   Coincidence? The glowies don't believe in those.        ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if GITHUB_TOKEN == "your_token_here":
        print("[!] Set your token: export GITHUB_TOKEN=ghp_...")
        print("[!] Nice try, glowie. Get your own token.\n")
        return

    print(f"Monitoring {len(REPOS)} repos every {CHECK_INTERVAL}s")
    print(f"Evidence file: {STATE_FILE}")
    print("Press Ctrl+C to go dark\n")

    try:
        while True:
            check_repos()
            print(f"\nNext sweep in {CHECK_INTERVAL}s... stay frosty.")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nGoing dark. But remember: they never stop watching.")
        print("Stay vigilant. Trust no one. Especially the glowies.\n")

if __name__ == "__main__":
    main()
