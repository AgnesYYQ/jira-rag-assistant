from fastapi import FastAPI, Request
from pydantic import BaseModel
import chromadb
import requests

app = FastAPI()
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("github_code")

class QueryRequest(BaseModel):
	question: str

@app.post("/query")
def query_rag(req: QueryRequest):
	# Retrieve top 5 relevant docs from Chroma
	results = collection.query(
		query_texts=[req.question],
		n_results=5,
		include=["documents", "metadatas"]
	)
	docs = results["documents"][0] if results["documents"] and results["documents"][0] else []
	metas = results["metadatas"][0] if results.get("metadatas") and results["metadatas"][0] else []
	# Build context and links
	context_blocks = []
	links = []
	for i, doc in enumerate(docs):
		meta = metas[i] if i < len(metas) else {}
		repo = meta.get("repo")
		path = meta.get("path")
		# Default to 'main' branch; adjust if you want to infer from metadata
		branch = "main"
		if repo and path:
			url = f"https://github.com/{repo}/blob/{branch}/{path}"
			links.append(url)
			context_blocks.append(f"[{repo}/{path}]({url}):\n{doc[:300]}{'...' if len(doc) > 300 else ''}")
		else:
			context_blocks.append(doc[:300] + ("..." if len(doc) > 300 else ""))
	context = "\n---\n".join(context_blocks)
	prompt = f"Context:\n{context}\n\nQuestion: {req.question}\nAnswer:"

	# Call Ollama (using installed 'llama3' model)
	ollama_resp = requests.post(
		"http://localhost:11434/api/generate",
		json={"model": "llama3", "prompt": prompt, "stream": False}
	)
	print("Ollama API response:", ollama_resp.json())  # Debug print
	answer = ollama_resp.json().get("response", "").strip()
	# Format answer with line breaks
	pretty_answer = "\n".join([line.strip() for line in answer.split("\n") if line.strip()])
	# Format links as a line-separated string for clarity
	links_str = "\n".join(links) if links else ""
	return {
		"answer": pretty_answer,
		"context": context,
		"links": links_str
	}
