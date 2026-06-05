import chromadb
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

from jirabot.query_scoring import confidence_from_distance, complexity_from_text

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
	include=["documents", "metadatas", "distances"]
)

print(f"\nTop results for query: '{query}'\n")
distances = results.get("distances", [[]])[0] if results.get("distances") else []
for i, doc in enumerate(results["documents"][0]):
	meta = results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else None
	distance = distances[i] if i < len(distances) else None
	confidence_score = confidence_from_distance(distance)
	complexity_score, complexity_label = complexity_from_text(doc)
	print(f"Result {i+1}:")
	if meta:
		print(f"  Metadata: {meta}")
	if distance is not None:
		print(f"  Distance: {distance:.4f}")
	if confidence_score is not None:
		print(f"  Confidence score: {confidence_score:.3f}")
	print(f"  Complexity score: {complexity_score:.3f} ({complexity_label})")
	print(f"  Document preview: {doc[:300]}{'...' if len(doc) > 300 else ''}")
	print()
