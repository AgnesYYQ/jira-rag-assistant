import chromadb
import sys

# Usage: python chroma_query.py "your search query"
if len(sys.argv) < 2:
	print("Usage: python chroma_query.py 'your search query'")
	sys.exit(1)

query = sys.argv[1]

# Connect to Chroma DB using persistent client and correct path
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("github_code")

# Print document count
count = collection.count()
print(f"Collection: github_code, Document count: {count}")

# Semantic similarity search
results = collection.query(
	query_texts=[query],
	n_results=5,
	include=["documents", "metadatas"]
)

print(f"\nTop results for query: '{query}'\n")
for i, doc in enumerate(results["documents"][0]):
	meta = results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else None
	print(f"Result {i+1}:")
	if meta:
		print(f"  Metadata: {meta}")
	print(f"  Document preview: {doc[:300]}{'...' if len(doc) > 300 else ''}")
	print()
