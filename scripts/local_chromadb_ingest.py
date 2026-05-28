"""
Ingest code from your GitHub public repos into Chroma vector DB for local RAG.
- Uses SentenceTransformers for embeddings
- Stores code file content and metadata in Chroma
- No KB JSON dependency; fetches directly from GitHub
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
                "content": code.text
            })
        if (i+1) % 10 == 0 or i == len(files)-1:
            print(f"[INFO]     Downloaded {i+1}/{len(files)} files...")
    return code_files

# --- 3. Ingest into Chroma ---
def ingest_all():
    print("[INFO] Starting Chroma ingestion...")
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_or_create_collection("github_code")
    embedder = SentenceTransformer(EMBED_MODEL)
    repos = list_repos(ORG)
    upserted = 0
    for repo in repos:
        print(f"[INFO] Ingesting repo: {repo}")
        code_files = fetch_code_files(ORG, repo)
        for j, file in enumerate(code_files):
            # Use deterministic ID: repo:path
            doc_id = f"{repo}:{file['path']}"
            doc = f"Repo: {repo}\nPath: {file['path']}\n\n{file['content']}"
            emb = embedder.encode([doc])[0]
            # Upsert: delete existing doc with same ID, then add
            try:
                collection.delete(ids=[doc_id])
            except Exception:
                pass
            collection.add(documents=[doc], embeddings=[emb], ids=[doc_id], metadatas=[{"repo": repo, "path": file["path"]}])
            upserted += 1
            if (j+1) % 10 == 0 or j == len(code_files)-1:
                print(f"[INFO]     Embedded {j+1}/{len(code_files)} files in {repo}...")
    print(f"[INFO] Ingested or updated {upserted} code files into Chroma.")

if __name__ == "__main__":
    ingest_all()
