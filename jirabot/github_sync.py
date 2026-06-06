"""
GitHub Code Sync Pipeline for VectorDB KB

- Fetches all code files from the default branch (main/master) of a GitHub repo and updates the KB JSON file.
- Does NOT sync issues or PRs.
- Intended to be run on a schedule (e.g., nightly).
- Requires GitHub token and KB path via environment variables.
"""
import os
import requests
import json
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
KB_PATH = os.environ.get("VECTOR_KB_PATH", "./kb_data/sample_kb.json")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
SYNC_META_PATH = os.path.join(os.path.dirname(KB_PATH), "sync_meta.json")

def get_default_branch(repo):
    url = f"https://api.github.com/repos/{repo}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("default_branch", "main")

def fetch_repo_tree(repo, branch):
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("tree", [])

def fetch_file_content(repo, file_sha):
    url = f"https://api.github.com/repos/{repo}/git/blobs/{file_sha}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    import base64
    content = resp.json().get("content", "")
    encoding = resp.json().get("encoding", "")
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    return content

def fetch_last_commit_author(repo: str, file_path: str) -> str | None:
    """Return the author name of the most recent commit touching *file_path*."""
    url = f"https://api.github.com/repos/{repo}/commits"
    params = {"path": file_path, "per_page": 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        commits = resp.json()
        if commits and isinstance(commits, list):
            author_info = commits[0].get("commit", {}).get("author", {})
            return author_info.get("name") or commits[0].get("author", {}).get("login")
    except Exception as exc:
        print(f"[WARN] Could not fetch author for {repo}/{file_path}: {exc}")
    return None


def sync_github_code_to_vector_db(
    repo,
    include_exts=(
        ".py", ".md", ".txt", ".go", ".java", ".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".rs", ".swift", ".kt", ".scala", ".sh", ".bat", ".ps1", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".css", ".scss", ".less", ".tf", ".dockerfile", ".makefile", ".gradle", ".pl", ".m", ".r", ".jl", ".dart", ".lua", ".sql", ".ipynb"
    )
):
    branch = get_default_branch(repo)
    tree = fetch_repo_tree(repo, branch)
    # Load existing KB
    if os.path.exists(KB_PATH):
        with open(KB_PATH) as f:
            kb = json.load(f)
    else:
        kb = []
    kb_by_id = {item.get("id"): item for item in kb}
    # Load last sync time
    last_sync = None
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
            last_sync = meta.get("github_last_sync")
    count = 0
    for entry in tree:
        if entry["type"] != "blob":
            continue
        path = entry["path"]
        if not any(path.endswith(ext) for ext in include_exts):
            continue
        # If incremental: skip files not updated since last sync (GitHub API doesn't provide last-modified in tree, so always sync all for now)
        file_id = f"gh_code_{repo}_{path}"
        content = fetch_file_content(repo, entry["sha"])
        filename = path.split("/")[-1]
        source_url = f"https://github.com/{repo}/blob/{branch}/{path}"
        # Fetch author from last commit
        author = fetch_last_commit_author(repo, path)
        kb_by_id[file_id] = {
            "id": file_id,
            "question": f"Code: {path}",
            "answer": content,
            "path": path,
            "repo": repo,
            "type": "github_code",
            # --- Citation ---
            "source": "github",
            "source_id": f"{repo}:{path}",
            "source_url": source_url,
            "title": filename,
            # --- Attribution ---
            "author": author,
            "updated": None,
        }
        count += 1
    # Save
    with open(KB_PATH, "w") as f:
        json.dump(list(kb_by_id.values()), f, indent=2)
    # Update sync_meta.json with current timestamp
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    if os.path.exists(SYNC_META_PATH):
        with open(SYNC_META_PATH) as f:
            meta = json.load(f)
    else:
        meta = {}
    meta["github_last_sync"] = now
    with open(SYNC_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Synced {count} code files from {repo} to KB. Last sync: {now}")

if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "yourorg/yourrepo"
    sync_github_code_to_vector_db(repo)
