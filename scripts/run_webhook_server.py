# This script is for local development/testing only.
# It runs the FastAPI webhook server for Jira events.
# See webhook_server.py for the actual implementation.

import uvicorn

if __name__ == "__main__":
    uvicorn.run("webhook_server:app", host="0.0.0.0", port=8000, reload=True)
