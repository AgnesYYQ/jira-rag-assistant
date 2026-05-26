"""
VectorDB: Simple vector database using FAISS and sentence-transformers.
"""
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os

class VectorDB:
    def __init__(self, kb_path, model_name='all-MiniLM-L6-v2'):
        self.kb_path = kb_path
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.data = []
        self.embeddings = None
        self._load_kb()

    def _load_kb(self):
        import re
        import datetime
        if not os.path.exists(self.kb_path):
            raise FileNotFoundError(f"KB file not found: {self.kb_path}")
        with open(self.kb_path, 'r') as f:
            raw_data = json.load(f)
        filtered = []
        now = datetime.datetime.utcnow()
        one_year_ago = now - datetime.timedelta(days=365)
        for item in raw_data:
            # Filter out obsolete wiki/code entries
            if any(
                re.search(r"obsolete", str(item.get(field, "")), re.IGNORECASE)
                for field in ["question", "answer", "folder", "wiki_title"]
            ):
                continue
            # Filter out old Jira issues (if date field exists)
            date_str = item.get("created") or item.get("date")
            if date_str:
                try:
                    dt = datetime.datetime.fromisoformat(date_str)
                    if dt < one_year_ago:
                        continue
                except Exception:
                    pass
            filtered.append(item)
        self.data = filtered
        questions = [item['question'] for item in self.data]
        if questions:
            self.embeddings = self.model.encode(questions, convert_to_numpy=True)
            self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
            self.index.add(self.embeddings)
        else:
            self.embeddings = None
            self.index = None

    def query(self, text, top_k=3):
        query_vec = self.model.encode([text], convert_to_numpy=True)
        D, I = self.index.search(query_vec, top_k)
        results = []
        for idx in I[0]:
            if idx < len(self.data):
                results.append(self.data[idx])
        return results
