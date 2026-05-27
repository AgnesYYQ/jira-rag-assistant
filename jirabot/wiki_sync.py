"""
Confluence Wiki Sync Pipeline for VectorDB

Features:
1. Automated sync with Confluence API (fetch, update, delete pages)
2. Obsolete/deprecated detection (by title, label, or content)
3. Change detection (timestamp/version)
4. Deletion handling (remove from vector DB if deleted/obsolete)

Usage:
- Run this script on a schedule (e.g., cron, Airflow, GitHub Actions)
- Requires Confluence API credentials and VectorDB path
"""
import requests
import os
import json
SYNC_META_PATH = os.path.join(os.path.dirname(KB_PATH), "sync_meta.json")
from jirabot.vector_db import VectorDB
from datetime import datetime

CONFLUENCE_API_URL = os.environ.get("CONFLUENCE_API_URL")
CONFLUENCE_USER = os.environ.get("CONFLUENCE_USER")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN")
KB_PATH = os.environ.get("VECTOR_KB_PATH", "./kb_data/sample_kb.json")

# --- 1. Fetch all pages (with update timestamps) ---
def fetch_confluence_pages(space_key, limit=100):
    # Incremental fetch: get all pages updated since last sync
    # Use pagination to fetch all results
    pages = []
    start = 0
    limit = 100
    last_sync = None
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
            last_sync = meta.get("wiki_last_sync")
    while True:
        url = f"{CONFLUENCE_API_URL}/rest/api/content"
        params = {
            "spaceKey": space_key,
            "expand": "version,metadata.labels,body.storage",
            "limit": limit,
            "start": start
        }
        if last_sync:
            # Confluence API: CQL for last modified
            params["cql"] = f"lastmodified >= '{last_sync}'"
        resp = requests.get(url, params=params, auth=(CONFLUENCE_USER, CONFLUENCE_TOKEN))
        resp.raise_for_status()
        results = resp.json().get("results", [])
        pages.extend(results)
        if len(results) < limit:
            break
        start += limit
    return pages

# --- 2. Detect obsolete/deprecated pages ---
def is_obsolete(page):
    title = page.get("title", "")
    labels = [l['name'] for l in page.get("metadata", {}).get("labels", {}).get("results", [])]
    body = page.get("body", {}).get("storage", {}).get("value", "")
    for field in [title, body] + labels:
        if "obsolete" in field.lower() or "deprecated" in field.lower() or "archived" in field.lower():
            return True
    return False

# --- 3. Change detection ---
def get_page_version(page):
    return page.get("version", {}).get("number", 1)

def get_page_updated(page):
    return page.get("version", {}).get("when")

# --- 4. Sync pipeline ---
def sync_confluence_to_vector_db(space_key):
    pages = fetch_confluence_pages(space_key)
    # Load existing KB
    if os.path.exists(KB_PATH):
        with open(KB_PATH) as f:
            kb = json.load(f)
    else:
        kb = []
    kb_by_id = {item.get("id"): item for item in kb}
    updated_kb = []
    for page in pages:
        page_id = page["id"]
        if is_obsolete(page):
            # Remove if present
            if page_id in kb_by_id:
                del kb_by_id[page_id]
            continue
        # Change detection
        version = get_page_version(page)
        updated = get_page_updated(page)
        # If new or updated, add/update
        kb_by_id[page_id] = {
            "id": page_id,
            "question": page["title"],
            "answer": page.get("body", {}).get("storage", {}).get("value", ""),
            "version": version,
            "updated": updated,
        }
    # Remove deleted pages
    page_ids = set(page["id"] for page in pages if not is_obsolete(page))
    for item in list(kb_by_id.values()):
        if item["id"] not in page_ids:
            continue  # skip deleted/obsolete
        updated_kb.append(item)
    # Save
    with open(KB_PATH, "w") as f:
        json.dump(updated_kb, f, indent=2)
    # Update sync_meta.json with current timestamp
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
    else:
        meta = {}
    meta["wiki_last_sync"] = now
    with open(SYNC_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Synced {len(updated_kb)} pages to KB. Last sync: {now}")

if __name__ == "__main__":
    # Example usage: python wiki_sync.py SPACEKEY
    import sys
    space_key = sys.argv[1] if len(sys.argv) > 1 else "YOURSPACE"
    sync_confluence_to_vector_db(space_key)
