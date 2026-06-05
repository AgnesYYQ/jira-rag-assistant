from scripts.local_chromadb_ingest import sync_repo_to_chroma


class FakeEmbedder:
    def encode(self, documents):
        return [[float(len(documents[0]))]]


class FakeCollection:
    def __init__(self, initial_items=None):
        self.items = initial_items or {}

    def get(self, where=None, include=None):
        repo = where.get("repo") if where else None
        ids = []
        metadatas = []
        for doc_id, item in self.items.items():
            if repo is not None and item["metadata"].get("repo") != repo:
                continue
            ids.append(doc_id)
            metadatas.append(item["metadata"])
        return {"ids": ids, "metadatas": metadatas}

    def upsert(self, documents, embeddings, ids, metadatas):
        for doc_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas):
            self.items[doc_id] = {
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
            }

    def delete(self, ids):
        for doc_id in ids:
            self.items.pop(doc_id, None)


def test_sync_repo_to_chroma_updates_changed_and_removes_deleted(monkeypatch):
    collection = FakeCollection(
        {
            "repo:keep.py": {
                "document": "old keep",
                "embedding": [1.0],
                "metadata": {"repo": "repo", "path": "keep.py", "sha": "old-sha"},
            },
            "repo:remove.py": {
                "document": "old remove",
                "embedding": [1.0],
                "metadata": {"repo": "repo", "path": "remove.py", "sha": "remove-sha"},
            },
        }
    )

    def fake_fetch_code_files(org, repo, include_exts=None):
        return [
            {"path": "keep.py", "content": "print('keep')", "sha": "old-sha"},
            {"path": "new.py", "content": "print('new')", "sha": "new-sha"},
        ]

    monkeypatch.setattr("scripts.local_chromadb_ingest.fetch_code_files", fake_fetch_code_files)

    stats = sync_repo_to_chroma("org", "repo", collection, FakeEmbedder())

    assert stats == {"updated": 1, "skipped": 1, "deleted": 1, "total": 2}
    assert "repo:remove.py" not in collection.items
    assert "repo:keep.py" in collection.items
    assert "repo:new.py" in collection.items
    assert collection.items["repo:keep.py"]["metadata"]["sha"] == "old-sha"
    assert collection.items["repo:new.py"]["metadata"]["sha"] == "new-sha"