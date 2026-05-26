# test_webhook_server.py
import pytest
from fastapi.testclient import TestClient
from webhook_server import app

client = TestClient(app)

def test_jira_webhook_accepts_valid_payload(monkeypatch):
    test_cases = [
        ( {"issue": {"key": "ABC-123"}, "webhookEvent": "jira:issue_created"}, "accepted", True ),
        ( {"issue": {"key": "ABC-123"}, "issue_event_type_name": "issue_created"}, "accepted", True ),
        ( {"issue": {"key": "ABC-123"}, "webhookEvent": "jira:issue_updated"}, "ignored", False ),
        ( {"issue": {"key": "ABC-123"}}, "ignored", False ),
    ]
    for payload, expected_status, should_call in test_cases:
        called = {}
        def fake_run_agent_on_ticket(ticket_key):
            called['ticket'] = ticket_key
        monkeypatch.setattr("webhook_server.run_agent_on_ticket", fake_run_agent_on_ticket)
        response = client.post("/webhook/jira", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == expected_status
        if expected_status == "accepted":
            assert response.json()["ticket"] == payload["issue"]["key"]
            assert called['ticket'] == payload["issue"]["key"]
        else:
            assert "reason" in response.json()
            assert not called

    def test_jira_webhook_accepts_valid_created_event(monkeypatch):
        called = {}
        def fake_run_agent_on_ticket(ticket_key):
            called['ticket'] = ticket_key
        monkeypatch.setattr("webhook_server.run_agent_on_ticket", fake_run_agent_on_ticket)
        payload = {"issue": {"key": "ABC-123"}, "webhookEvent": "jira:issue_created"}
        response = client.post("/webhook/jira", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert response.json()["ticket"] == "ABC-123"
        assert response.json()["event"] == "jira:issue_created"
        assert called['ticket'] == "ABC-123"

    def test_jira_webhook_rejects_non_created_event():
        payload = {"issue": {"key": "ABC-123"}, "webhookEvent": "jira:issue_updated"}
        response = client.post("/webhook/jira", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert "not handled" in response.json()["reason"]

    def test_jira_webhook_rejects_missing_ticket_key():
        payload = {"webhookEvent": "jira:issue_created"}
        response = client.post("/webhook/jira", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert "No ticket key" in response.json()["reason"]

    def test_jira_webhook_accepts_issue_event_type_name(monkeypatch):
        called = {}
        def fake_run_agent_on_ticket(ticket_key):
            called['ticket'] = ticket_key
        monkeypatch.setattr("webhook_server.run_agent_on_ticket", fake_run_agent_on_ticket)
        payload = {"issue": {"key": "XYZ-789"}, "issue_event_type_name": "issue_created"}
        response = client.post("/webhook/jira", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        assert response.json()["ticket"] == "XYZ-789"
        assert response.json()["event"] == "issue_created"
        assert called['ticket'] == "XYZ-789"

    def test_jira_webhook_get_method_not_allowed():
        response = client.get("/webhook/jira")
        assert response.status_code == 405

def test_jira_webhook_ignores_invalid_payload():
    payload = {"foo": "bar"}
    response = client.post("/webhook/jira", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
