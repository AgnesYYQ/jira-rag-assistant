"""
Jira Sync Pipeline for VectorDB KB

- Fetches all issues from a Jira project and updates the KB JSON file.
- Intended to be run on a schedule (e.g., nightly).
- Requires Jira API credentials and KB path via environment variables.
"""
import os
import requests
import json
SYNC_META_PATH = os.path.join(os.path.dirname(KB_PATH), "sync_meta.json")
from datetime import datetime

JIRA_API_URL = os.environ.get("JIRA_API_URL")
JIRA_USER = os.environ.get("JIRA_USER")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
KB_PATH = os.environ.get("VECTOR_KB_PATH", "./kb_data/sample_kb.json")


def fetch_jira_issues(project_key, max_results=100):
    # Incremental fetch: get all issues updated since last sync
    # Use pagination to fetch all results
    issues = []
    start_at = 0
    max_results = 100
    last_sync = None
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
            last_sync = meta.get("jira_last_sync")
    while True:
        url = f"{JIRA_API_URL}/rest/api/3/search"
        jql = f"project={project_key}"
        if last_sync:
            jql += f" AND updated >= '{last_sync}'"
        jql += " ORDER BY created DESC"
        params = {"jql": jql, "maxResults": max_results, "startAt": start_at}
        resp = requests.get(url, params=params, auth=(JIRA_USER, JIRA_TOKEN))
        resp.raise_for_status()
        results = resp.json().get("issues", [])
        issues.extend(results)
        if len(results) < max_results:
            break
        start_at += max_results
    return issues


def sync_jira_to_vector_db(project_key):
    issues = fetch_jira_issues(project_key)
    # Load existing KB
    if os.path.exists(KB_PATH):
        with open(KB_PATH) as f:
            kb = json.load(f)
    else:
        kb = []
    kb_by_id = {item.get("id"): item for item in kb}
    filtered_issues = []
    for issue in issues:
        fields = issue["fields"]
        status = fields.get("status", {}).get("name", "")
        resolution = fields.get("resolution", {}).get("name", "")
        if status != "Closed" or resolution != "Solved":
            continue
        issue_id = issue["id"]
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        created = fields.get("created", "")
        kb_by_id[issue_id] = {
            "id": issue_id,
            "question": summary,
            "answer": description,
            "created": created,
            "status": status,
            "resolution": resolution,
            "type": "jira_issue"
        }
        filtered_issues.append(issue)
    # Save
    with open(KB_PATH, "w") as f:
        json.dump(list(kb_by_id.values()), f, indent=2)
    # Update sync_meta.json with current timestamp
    from datetime import datetime
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
    else:
        meta = {}
    meta["jira_last_sync"] = now
    with open(SYNC_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Synced {len(filtered_issues)} Closed/Solved Jira issues to KB. Last sync: {now}")

if __name__ == "__main__":
    import sys
    project_key = sys.argv[1] if len(sys.argv) > 1 else "YOURPROJECT"
    sync_jira_to_vector_db(project_key)
