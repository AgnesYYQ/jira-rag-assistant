"""
Utility to remove duplicate documents from Chroma collection 'github_code'.
Duplicates are detected by (repo, path) metadata.
"""
import chromadb

client = chromadb.Client()
collection = client.get_or_create_collection("github_code")

# Fetch all documents and their metadata
results = collection.get(include=["metadatas"])
seen = set()
dups = []
for idx, meta in enumerate(results["metadatas"]):
    key = (meta["repo"], meta["path"])
    if key in seen:
        dups.append(results["ids"][idx])
    else:
        seen.add(key)

if dups:
    print(f"Found {len(dups)} duplicate documents. Removing...")
    collection.delete(ids=dups)
    print("Duplicates removed.")
else:
    print("No duplicates found.")
