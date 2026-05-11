from fastapi import FastAPI, Request, BackgroundTasks
from jirabot import main as jirabot_main
import logging

app = FastAPI()


@app.post("/webhook/jira")
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    issue = payload.get("issue", {})
    ticket_key = issue.get("key")
    # Check for event type (Jira sends either 'webhookEvent' or 'issue_event_type_name')
    event_type = payload.get("webhookEvent") or payload.get("issue_event_type_name")
    if not ticket_key:
        return {"status": "ignored", "reason": "No ticket key"}
    if event_type not in ("jira:issue_created", "issue_created"):
        return {"status": "ignored", "reason": f"Event type {event_type} not handled"}
    # Run the agent logic in the background
    background_tasks.add_task(run_agent_on_ticket, ticket_key)
    return {"status": "accepted", "ticket": ticket_key, "event": event_type}

def run_agent_on_ticket(ticket_key: str):
    import sys
    import types
    # Simulate CLI args for main.py
    sys.argv = ["main.py", "--ticket", ticket_key]
    try:
        jirabot_main.main()
    except SystemExit:
        pass
    except Exception as e:
        logging.exception(f"Error running agent for ticket {ticket_key}: {e}")
