from fastapi.testclient import TestClient

from scripts import rag_server


class FakeCollection:
    def query(self, query_texts, n_results, include):
        return {
            "documents": [["def sample():\n    return True"]],
            "metadatas": [[{"repo": "org/repo", "path": "sample.py"}]],
            "distances": [[0.25]],
        }


class FakeResponse:
    def json(self):
        return {"response": "Use the sample implementation."}


def test_query_endpoint_returns_retrieval_scores(monkeypatch):
    monkeypatch.setattr(rag_server, "collection", FakeCollection())
    monkeypatch.setattr(rag_server.requests, "post", lambda *args, **kwargs: FakeResponse())

    client = TestClient(rag_server.app)
    response = client.post("/query", json={"question": "How does this work?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Use the sample implementation."
    assert payload["retrieval_results"][0]["distance"] == 0.25
    assert payload["retrieval_results"][0]["confidence_score"] == 0.8
    assert payload["retrieval_results"][0]["complexity_label"] in {"low", "medium", "high"}


def test_home_route_serves_html():
    client = TestClient(rag_server.app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "JiraBot Query Demo" in response.text