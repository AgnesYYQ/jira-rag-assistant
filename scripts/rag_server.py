import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import chromadb
import requests
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
	sys.path.insert(0, str(ROOT_DIR))

from jirabot.query_scoring import (
    confidence_from_distance,
    complexity_from_text,
    format_citation,
    format_citation_markdown,
)

# GitHub owner/org — used to construct proper source URLs when the stored
# repo metadata does not include the owner prefix (e.g. "jira-rag-assistant"
# instead of "AgnesYYQ/jira-rag-assistant").
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "AgnesYYQ")


def _full_repo(repo: str | None) -> str | None:
    """Return the full ``owner/repo`` string.

    If *repo* already contains a ``/`` it is returned as-is; otherwise
    ``GITHUB_OWNER`` is prepended.
    """
    if not repo:
        return None
    return repo if "/" in repo else f"{GITHUB_OWNER}/{repo}"


app = FastAPI()
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("github_code")

# Same embedding model used during ingestion
_embed_model = SentenceTransformer("all-MiniLM-L6-v2")


@app.get("/", response_class=HTMLResponse)
def home():
	return """
<!doctype html>
<html lang="en">
<head>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<title>JiraBot Query Demo</title>
	<style>
		:root {
			color-scheme: light;
			--bg: #f6f3ee;
			--card: #ffffff;
			--ink: #1f2937;
			--muted: #6b7280;
			--accent: #0f766e;
			--accent-2: #155e75;
			--border: #e5e7eb;
			--shadow: 0 18px 50px rgba(15, 23, 42, 0.10);
		}
		body {
			margin: 0;
			font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
			color: var(--ink);
			background:
				radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 28%),
				radial-gradient(circle at top right, rgba(21, 94, 117, 0.10), transparent 24%),
				var(--bg);
			min-height: 100vh;
		}
		.wrap {
			max-width: 1060px;
			margin: 0 auto;
			padding: 40px 20px 56px;
		}
		.hero {
			display: grid;
			gap: 14px;
			margin-bottom: 24px;
		}
		.eyebrow {
			text-transform: uppercase;
			letter-spacing: 0.14em;
			font-size: 12px;
			color: var(--accent);
			font-weight: 700;
		}
		h1 {
			margin: 0;
			font-size: clamp(2rem, 4vw, 3.6rem);
			line-height: 1.05;
		}
		.sub {
			margin: 0;
			color: var(--muted);
			max-width: 72ch;
			font-size: 1.05rem;
			line-height: 1.6;
		}
		.grid {
			display: grid;
			grid-template-columns: 1.1fr 0.9fr;
			gap: 20px;
			align-items: start;
		}
		@media (max-width: 900px) {
			.grid { grid-template-columns: 1fr; }
		}
		.panel {
			background: rgba(255, 255, 255, 0.82);
			backdrop-filter: blur(12px);
			border: 1px solid var(--border);
			border-radius: 22px;
			box-shadow: var(--shadow);
			padding: 20px;
		}
		label {
			display: block;
			font-size: 0.95rem;
			font-weight: 700;
			margin-bottom: 10px;
		}
		textarea {
			width: 100%;
			min-height: 120px;
			resize: vertical;
			border: 1px solid var(--border);
			border-radius: 14px;
			padding: 14px;
			font: inherit;
			box-sizing: border-box;
			background: #fff;
		}
		button {
			margin-top: 12px;
			border: none;
			border-radius: 999px;
			padding: 12px 18px;
			font: inherit;
			font-weight: 700;
			color: white;
			background: linear-gradient(135deg, var(--accent), var(--accent-2));
			cursor: pointer;
		}
		button:hover { opacity: 0.95; }
		.muted { color: var(--muted); }
		.stack { display: grid; gap: 14px; }
		.answer {
			white-space: pre-wrap;
			line-height: 1.6;
			padding: 16px;
			background: #f8fafc;
			border: 1px solid var(--border);
			border-radius: 16px;
		}
		.card {
			border: 1px solid var(--border);
			border-radius: 16px;
			padding: 14px 16px;
			background: #fff;
		}
		.meta {
			font-size: 0.92rem;
			color: var(--muted);
			display: flex;
			flex-wrap: wrap;
			gap: 10px;
			margin-bottom: 8px;
		}
		.score {
			font-weight: 700;
			color: var(--accent-2);
		}
		pre {
			margin: 0;
			white-space: pre-wrap;
			word-break: break-word;
			font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
			font-size: 0.9rem;
			line-height: 1.55;
		}
		.links a { color: var(--accent-2); text-decoration: none; }
		.links a:hover { text-decoration: underline; }
		.citation-link { color: var(--accent-2); text-decoration: none; }
		.citation-link:hover { text-decoration: underline; }
	</style>
</head>
<body>
	<div class="wrap">
		<section class="hero">
			<div class="eyebrow">JiraBot Query Demo</div>
			<h1>Search the GitHub Chroma collection and read the result cleanly.</h1>
			<p class="sub">Enter a question, get the generated answer, and inspect the retrieval cards with distance, confidence, and complexity scores.</p>
		</section>

		<div class="grid">
			<div class="panel">
				<label for="question">Question</label>
				<textarea id="question">rag agent</textarea>
				<button id="searchBtn">Ask JiraBot</button>
				<p class="muted" id="status" style="margin-bottom:0;"></p>
			</div>

			<div class="panel stack">
				<div>
					<label>Answer</label>
					<div class="answer" id="answer">Run a query to see the result here.</div>
				</div>
				<div>
					<label>Links</label>
					<div class="links muted" id="links">No links yet.</div>
				</div>
			</div>
		</div>

		<div class="panel stack" style="margin-top:20px;">
			<div>
				<label>Retrieval Results</label>
				<div class="stack" id="results"></div>
			</div>
		</div>
	</div>

	<script>
		const questionEl = document.getElementById('question');
		const answerEl = document.getElementById('answer');
		const linksEl = document.getElementById('links');
		const resultsEl = document.getElementById('results');
		const statusEl = document.getElementById('status');
		const btn = document.getElementById('searchBtn');

		function setStatus(message) {
			statusEl.textContent = message;
		}

		function renderResults(items) {
			if (!items || !items.length) {
				resultsEl.innerHTML = '<div class="card muted">No retrieval results.</div>';
				return;
			}

			resultsEl.innerHTML = items.map((item) => {
				const meta = item.metadata || {};
				const metaText = [meta.repo, meta.path].filter(Boolean).join(' / ');
				const distance = item.distance == null ? 'n/a' : Number(item.distance).toFixed(4);			const cosineSim = item.cosine_similarity == null ? 'n/a' : Number(item.cosine_similarity).toFixed(4);				const confidence = item.confidence_score == null ? 'n/a' : Number(item.confidence_score).toFixed(3);
				const complexity = item.complexity_score == null ? 'n/a' : Number(item.complexity_score).toFixed(3);
				const citation = item.citation || metaText || 'unknown source';
				const sourceUrl = item.source_url || '';
				const citationHtml = sourceUrl
					? `<a href="${sourceUrl}" target="_blank" rel="noreferrer" class="citation-link">${citation}</a>`
					: citation;
				return `
					<article class="card">
						<div class="meta">
							<span>Rank ${item.rank}</span>
							<span class="score">${citationHtml}</span>
							<span>Distance <strong>${distance}</strong></span>
							<span>CosSim <strong>${cosineSim}</strong></span>
							<span>Confidence <strong class="score">${confidence}</strong></span>
							<span>Complexity <strong>${complexity}</strong> (${item.complexity_label || 'n/a'})</span>
						</div>
						<pre>${item.preview || ''}</pre>
					</article>
				`;
			}).join('');
		}

		async function ask() {
			const question = questionEl.value.trim();
			if (!question) {
				setStatus('Type a question first.');
				return;
			}

			btn.disabled = true;
			setStatus('Searching and generating a response...');
			try {
				const response = await fetch('/query', {
					method: 'POST',
					headers: {'Content-Type': 'application/json'},
					body: JSON.stringify({question}),
				});
				const data = await response.json();
				answerEl.textContent = data.answer || 'No answer returned.';
				linksEl.innerHTML = data.links
					? data.links.split('\\n').map((link) => `<div><a href="${link}" target="_blank" rel="noreferrer">${link}</a></div>`).join('')
					: '<span class="muted">No links returned.</span>';
				renderResults(data.retrieval_results || []);
				setStatus('Done.');
			} catch (error) {
				console.error(error);
				setStatus('Query failed. Make sure the server, Ollama, and Chroma are running.');
				resultsEl.innerHTML = '<div class="card muted">Unable to load results.</div>';
			} finally {
				btn.disabled = false;
			}
		}

		btn.addEventListener('click', ask);
		questionEl.addEventListener('keydown', (event) => {
			if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
				ask();
			}
		});
	</script>
</body>
</html>
"""

class QueryRequest(BaseModel):
	question: str

@app.post("/query")
def query_rag(req: QueryRequest):
	# Compute query embedding for cosine similarity
	query_emb = _embed_model.encode([req.question], convert_to_numpy=True)[0]
	# Retrieve top 5 relevant docs from Chroma (include embeddings for similarity)
	results = collection.query(
		query_texts=[req.question],
		n_results=5,
		include=["documents", "metadatas", "distances", "embeddings"]
	)
	docs = results["documents"][0] if results["documents"] and results["documents"][0] else []
	metas = results["metadatas"][0] if results.get("metadatas") and results["metadatas"][0] else []
	distances = results.get("distances", [[]])[0] if results.get("distances") else []
	# Build context and links
	context_blocks = []
	links = []
	retrieval_results = []
	for i, doc in enumerate(docs):
		meta = metas[i] if i < len(metas) else {}
		distance = distances[i] if i < len(distances) else None
		confidence_score = confidence_from_distance(distance)
		complexity_score, complexity_label = complexity_from_text(doc)
		repo = meta.get("repo")
		path = meta.get("path")
		full_repo = _full_repo(repo)
		# Default to 'main' branch; adjust if you want to infer from metadata
		branch = "main"
		if full_repo and path:
			url = f"https://github.com/{full_repo}/blob/{branch}/{path}"
			links.append(url)
			context_blocks.append(f"[{full_repo}/{path}]({url}):\n{doc[:300]}{'...' if len(doc) > 300 else ''}")
		else:
			context_blocks.append(doc[:300] + ("..." if len(doc) > 300 else ""))
		# Build citation/attribution from available metadata
		author = meta.get("author")
		item_with_source = {
			"source": "github",
			"source_id": f"{full_repo}/{path}" if full_repo and path else "",
			"source_url": url if full_repo and path else "",
			"title": path.split("/")[-1] if path else "",
			"author": author,
		}
		# Cosine similarity between query and this result's stored embedding
		embeddings = results.get("embeddings", [[]])[0] if results.get("embeddings") else []
		stored_emb = embeddings[i] if i < len(embeddings) else None
		if stored_emb is not None:
			dot = float(np.dot(query_emb, stored_emb))
			norm = float(np.linalg.norm(query_emb)) * float(np.linalg.norm(stored_emb))
			cosine_sim = round(dot / norm, 4) if norm > 0 else 0.0
		else:
			cosine_sim = None

		retrieval_results.append({
			"rank": i + 1,
			"metadata": meta,
			"distance": distance,
			"cosine_similarity": cosine_sim,
			"confidence_score": confidence_score,
			"complexity_score": complexity_score,
			"complexity_label": complexity_label,
			"citation": format_citation(item_with_source),
			"citation_markdown": format_citation_markdown(item_with_source),
			"source_url": url if repo and path else "",
			"preview": doc[:300] + ("..." if len(doc) > 300 else ""),
		})
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
		"links": links_str,
		"retrieval_results": retrieval_results,
	}
