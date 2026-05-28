"""
Nightly sync script for Jira, GitHub, and Wiki resources.
- Runs all sync pipelines to refresh the vector DB KB with up-to-date data from all sources.
- Intended to be scheduled (e.g., via cron, Airflow, or GitHub Actions).

Assumes:
- jirabot/wiki_sync.py handles Confluence Wiki
- jirabot/jira_sync.py handles Jira issues (to KB)
- jirabot/github_sync.py handles GitHub issues/PRs (to KB)

You may need to implement jira_sync.py and github_sync.py if not present.
"""
import subprocess
import sys
import os

# Paths to sync scripts
WIKI_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/wiki_sync.py")
JIRA_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/jira_sync.py")
GITHUB_SYNC = os.path.join(os.path.dirname(__file__), "jirabot/github_sync.py")

# Example: pass space key for wiki, project key for Jira, repo for GitHub
WIKI_SPACE = os.environ.get("WIKI_SPACE", "YOURSPACE")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "YOURPROJECT")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "yourorg/yourrepo")


def run_script(script, args=None):
    cmd = [sys.executable, script]
    if args:
        cmd += args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Script {script} failed")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync KB from Wiki, Jira, and/or GitHub.")
    parser.add_argument('--wiki', action='store_true', help='Sync Wiki')
    parser.add_argument('--jira', action='store_true', help='Sync Jira')
    parser.add_argument('--github', action='store_true', help='Sync GitHub')
    args = parser.parse_args()

    # If no args, sync all (default for nightly)
    if not (args.wiki or args.jira or args.github):
        run_script(WIKI_SYNC, [WIKI_SPACE])
        run_script(JIRA_SYNC, [JIRA_PROJECT])
        run_script(GITHUB_SYNC, [GITHUB_REPO])
        print("Nightly sync completed.")
        return
    if args.wiki:
        run_script(WIKI_SYNC, [WIKI_SPACE])
    if args.jira:
        run_script(JIRA_SYNC, [JIRA_PROJECT])
    if args.github:
        run_script(GITHUB_SYNC, [GITHUB_REPO])
    print("Selected sync completed.")

if __name__ == "__main__":
    main()
