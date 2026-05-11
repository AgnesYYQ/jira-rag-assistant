# test_webhook_server.py
import pytest
from fastapi.testclient import TestClient
from webhook_server import app

client = TestClient(app)

def test_jira_webhook_accepts_valid_payload(monkeypatch):
    called = {}
    def fake_run_agent_on_ticket(ticket_key):
        called['ticket'] = ticket_key
    monkeypatch.setattr("webhook_server.run_agent_on_ticket", fake_run_agent_on_ticket)
    payload = {"issue": {"key": "ABC-123"}}
    response = client.post("/webhook/jira", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert response.json()["ticket"] == "ABC-123"
    assert called['ticket'] == "ABC-123"

def test_jira_webhook_ignores_invalid_payload():
    payload = {"foo": "bar"}
    response = client.post("/webhook/jira", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
