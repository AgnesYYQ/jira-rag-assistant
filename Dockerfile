# Dockerfile for JiraBot Webhook Server
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn
COPY . .
EXPOSE 8000
CMD ["uvicorn", "webhook_server:app", "--host", "0.0.0.0", "--port", "8000"]
