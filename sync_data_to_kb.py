"""
Sync data from GitHub (and optionally Jira/Wiki) into the vector DB KB.

- Runs all sync pipelines to refresh the KB with up-to-date data.
- Intended to be scheduled (cron, GitHub Actions, Airflow, etc.) or run manually.
- By default syncs GitHub code only. Jira and Wiki are optional — skipped when
  their required env vars are not set.

Assumes:
- jirabot/wiki_sync.py handles Confluence Wiki
- jirabot/jira_sync.py handles Jira issues (to KB)
- jirabot/github_sync.py handles GitHub code sync (to KB)
"""
import subprocess
import sys
import os

# Paths to sync scripts
WIKI_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/wiki_sync.py")
JIRA_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/jira_sync.py")
GITHUB_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/github_sync.py")

# Env vars
GITHUB_REPO = os.environ.get("GITHUB_REPO")
WIKI_SPACE = os.environ.get("WIKI_SPACE")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT")


def _wiki_available() -> bool:
    return bool(WIKI_SPACE and os.environ.get("CONFLUENCE_API_URL"))


def _jira_available() -> bool:
    return bool(JIRA_PROJECT and os.environ.get("JIRA_API_URL"))


def run_script(script, args=None):
    cmd = [sys.executable, script]
    if args:
        cmd += args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr)
        return False
    return True


def try_sync(name: str, script: str, args: list | None, required_vars_ok: bool):
    """Run *script* if *required_vars_ok* is True, otherwise print a skip notice."""
    if not required_vars_ok:
        print(f"[SKIP] {name}: required env vars not set — skipping.")
        return
    print(f"[SYNC] {name}: starting...")
    ok = run_script(script, args)
    if ok:
        print(f"[SYNC] {name}: completed.")
    else:
        print(f"[WARN] {name}: sync failed (check logs above). Continuing with remaining syncs.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync KB from Wiki, Jira, and/or GitHub.")
    parser.add_argument('--wiki', action='store_true', help='Sync Wiki')
    parser.add_argument('--jira', action='store_true', help='Sync Jira')
    parser.add_argument('--github', action='store_true', help='Sync GitHub')
    args = parser.parse_args()

    # If no specific flags, default: sync GitHub (always), Wiki and Jira if available
    if not (args.wiki or args.jira or args.github):
        try_sync("GitHub", GITHUB_SYNC, [GITHUB_REPO] if GITHUB_REPO else None,
                 required_vars_ok=bool(GITHUB_REPO))
        try_sync("Wiki", WIKI_SYNC, [WIKI_SPACE], _wiki_available())
        try_sync("Jira", JIRA_SYNC, [JIRA_PROJECT], _jira_available())
        print("Nightly sync completed.")
        return

    if args.github:
        try_sync("GitHub", GITHUB_SYNC, [GITHUB_REPO] if GITHUB_REPO else None,
                 required_vars_ok=bool(GITHUB_REPO))
    if args.wiki:
        try_sync("Wiki", WIKI_SYNC, [WIKI_SPACE], _wiki_available())
    if args.jira:
        try_sync("Jira", JIRA_SYNC, [JIRA_PROJECT], _jira_available())
    print("Selected sync completed.")

if __name__ == "__main__":
    main()
