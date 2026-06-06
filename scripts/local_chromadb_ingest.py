"""
Ingest code from your GitHub public repos into Chroma vector DB for local RAG.
- Uses SentenceTransformers for embeddings
- Stores code file content and metadata in Chroma
- No KB JSON dependency; fetches directly from GitHub
- Syncs incrementally by comparing GitHub blob SHAs with stored Chroma metadata
"""
import os
import requests
import chromadb
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
ORG = "AgnesYYQ"  # Your GitHub org
INCLUDE_EXTS = (
    ".py", ".md", ".txt", ".go", ".java", ".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".rs", ".swift", ".kt", ".scala", ".sh", ".bat", ".ps1", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".css", ".scss", ".less", ".tf", ".dockerfile", ".makefile", ".gradle", ".pl", ".m", ".r", ".jl", ".dart", ".lua", ".sql", ".ipynb"
)
EMBED_MODEL = "all-MiniLM-L6-v2"

# GitHub auth headers (optional — used to raise the rate limit from 60 to 5000 req/hr)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
_GH_HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def fetch_last_commit_author(org: str, repo: str, file_path: str) -> str | None:
    """Return the author name of the most recent commit touching *file_path*."""
    url = f"https://api.github.com/repos/{org}/{repo}/commits"
    params = {"path": file_path, "per_page": 1}
    try:
        resp = requests.get(url, params=params, headers=_GH_HEADERS, timeout=10)
        resp.raise_for_status()
        commits = resp.json()
        if commits and isinstance(commits, list):
            author_info = commits[0].get("commit", {}).get("author", {})
            return author_info.get("name") or commits[0].get("author", {}).get("login")
    except Exception as exc:
        print(f"[WARN] Could not fetch author for {org}/{repo}/{file_path}: {exc}")
    return None

# --- 1. List all public repos in the org ---
def list_repos(org):
    url = f"https://api.github.com/users/{org}/repos"
    repos = []
    page = 1
    print(f"[INFO] Fetching repo list for org: {org}")
    while True:
        print(f"[INFO]  - Fetching page {page} of repos...")
        resp = requests.get(url, params={"per_page": 100, "page": page})
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend([r["name"] for r in data])
        page += 1
    print(f"[INFO] Found {len(repos)} repos in {org}")
    return repos

# --- 2. Fetch code files from a repo ---
def fetch_code_files(org, repo, include_exts=INCLUDE_EXTS):
    # Get default branch for this repo
    repo_info = requests.get(f"https://api.github.com/repos/{org}/{repo}").json()
    branch = repo_info.get("default_branch", "main")
    url = f"https://api.github.com/repos/{org}/{repo}/git/trees/{branch}?recursive=1"
    print(f"[INFO]   Fetching file tree for repo: {repo} (branch: {branch})")
    resp = requests.get(url)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])
    files = [f for f in tree if f["type"] == "blob" and any(f["path"].endswith(ext) for ext in include_exts)]
    print(f"[INFO]   Found {len(files)} code files in {repo}")
    code_files = []
    for i, f in enumerate(files):
        raw_url = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{f['path']}"
        code = requests.get(raw_url)
        if code.status_code == 200:
            code_files.append({
                "repo": repo,
                "path": f["path"],
                "sha": f["sha"],
                "content": code.text,
            })
        if (i+1) % 10 == 0 or i == len(files)-1:
            print(f"[INFO]     Downloaded {i+1}/{len(files)} files...")
    return code_files

def _collection_items_by_repo(collection, repo):
    existing = collection.get(where={"repo": repo}, include=["metadatas"])
    items = {}
    for doc_id, metadata in zip(existing.get("ids", []), existing.get("metadatas", [])):
        if not metadata:
            continue
        path = metadata.get("path")
        if path:
            items[path] = {"id": doc_id, "metadata": metadata}
    return items

def sync_repo_to_chroma(org, repo, collection, embedder, include_exts=INCLUDE_EXTS):
    """Sync one GitHub repo into the Chroma collection.

    Returns a dict with counts for updated, skipped, and deleted files.
    """
    full_repo_name = f"{org}/{repo}"
    code_files = fetch_code_files(org, repo, include_exts=include_exts)
    current_by_path = {file["path"]: file for file in code_files}
    existing_by_path = _collection_items_by_repo(collection, full_repo_name)

    updated = 0
    skipped = 0

    for file_path, file in current_by_path.items():
        existing = existing_by_path.get(file_path)
        if existing and existing["metadata"].get("sha") == file["sha"]:
            skipped += 1
            continue

        # Fetch the last commit author for attribution
        author = fetch_last_commit_author(org, repo, file_path)

        doc_id = f"{full_repo_name}:{file_path}"
        doc = f"Repo: {full_repo_name}\nPath: {file_path}\n\n{file['content']}"
        emb = embedder.encode([doc])[0]
        metadata = {
            "repo": full_repo_name,
            "path": file_path,
            "sha": file["sha"],
            "author": author,
        }

        if hasattr(collection, "upsert"):
            collection.upsert(documents=[doc], embeddings=[emb], ids=[doc_id], metadatas=[metadata])
        else:
            try:
                collection.delete(ids=[doc_id])
            except Exception:
                pass
            collection.add(documents=[doc], embeddings=[emb], ids=[doc_id], metadatas=[metadata])
        updated += 1

    removed_paths = sorted(set(existing_by_path) - set(current_by_path))
    removed_ids = [existing_by_path[path]["id"] for path in removed_paths]
    if removed_ids:
        collection.delete(ids=removed_ids)

    return {
        "updated": updated,
        "skipped": skipped,
        "deleted": len(removed_ids),
        "total": len(current_by_path),
    }

# --- 3. Ingest into Chroma ---
def ingest_all():
    print("[INFO] Starting Chroma ingestion...")
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection("github_code")
    embedder = SentenceTransformer(EMBED_MODEL)
    repos = list_repos(ORG)
    updated = 0
    skipped = 0
    deleted = 0
    for repo in repos:
        print(f"[INFO] Ingesting repo: {repo}")
        stats = sync_repo_to_chroma(ORG, repo, collection, embedder)
        updated += stats["updated"]
        skipped += stats["skipped"]
        deleted += stats["deleted"]
        print(
            f"[INFO]     Synced {repo}: {stats['updated']} updated, "
            f"{stats['skipped']} unchanged, {stats['deleted']} deleted"
        )
    print(
        f"[INFO] Sync complete. {updated} updated, {skipped} unchanged, {deleted} deleted."
    )

if __name__ == "__main__":
    ingest_all()
