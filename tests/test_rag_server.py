from fastapi.testclient import TestClient

from scripts import rag_server


def test_full_repo_with_slash_returns_as_is():
    """_full_repo should return repos already containing '/' unchanged."""
    assert rag_server._full_repo("AgnesYYQ/jira-rag-assistant") == "AgnesYYQ/jira-rag-assistant"
    assert rag_server._full_repo("org/repo") == "org/repo"


def test_full_repo_without_slash_prepends_owner(monkeypatch):
    """_full_repo should prepend GITHUB_OWNER when repo has no '/'."""
    monkeypatch.setattr(rag_server, "GITHUB_OWNER", "AgnesYYQ")
    assert rag_server._full_repo("jira-rag-assistant") == "AgnesYYQ/jira-rag-assistant"


def test_full_repo_none():
    """_full_repo should return None when given None."""
    assert rag_server._full_repo(None) is None


def test_full_repo_empty():
    """_full_repo should return None when given empty string."""
    assert rag_server._full_repo("") is None


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


def test_query_url_includes_owner_when_repo_is_bare(monkeypatch):
    """source_url should contain the full owner/repo even when metadata only has bare repo."""
    monkeypatch.setattr(rag_server, "GITHUB_OWNER", "AgnesYYQ")

    class FakeCollectionBare:
        def query(self, query_texts, n_results, include):
            return {
                "documents": [["def sample():\n    return True"]],
                "metadatas": [[{"repo": "jira-rag-assistant", "path": "sample.py"}]],
                "distances": [[0.25]],
            }

    monkeypatch.setattr(rag_server, "collection", FakeCollectionBare())
    monkeypatch.setattr(rag_server.requests, "post", lambda *args, **kwargs: FakeResponse())

    client = TestClient(rag_server.app)
    response = client.post("/query", json={"question": "test"})

    assert response.status_code == 200
    payload = response.json()
    url = payload["retrieval_results"][0]["source_url"]
    assert url == "https://github.com/AgnesYYQ/jira-rag-assistant/blob/main/sample.py"
    assert "AgnesYYQ/jira-rag-assistant/sample.py" in payload["context"]


def test_home_route_serves_html():
    client = TestClient(rag_server.app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "JiraBot Query Demo" in response.text