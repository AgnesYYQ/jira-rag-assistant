# JiraBot: Bedrock RAG-Powered JIRA Comment Assistant

## Overview
JiraBot leverages AWS Bedrock, a unified knowledge base (RAG), and JIRA APIs to generate high-quality, context-aware comments for JIRA tickets. It integrates data from Confluence, JIRA, GitHub, and S3, using vector search and LLMs for retrieval-augmented generation.

## Features
- Unified knowledge base (vector DB) with Wiki, JIRA, GitHub, and S3 sources
- Retrieval-augmented generation (RAG) using AWS Bedrock
- Automated JIRA comment drafting and posting
- Source citation in generated comments
- Modular, extensible Python codebase


## Architecture Diagram

```mermaid
graph TD

  User["User"]
  CLI["CLI / Script"]
  Agent["Agent Logic (agent.py)"]
  Bedrock["Amazon Bedrock"]
  Retriever["AmazonKnowledgeBasesRetriever"]
  JiraAPI["Jira API"]
  KnowledgeBase["Knowledge Base"]
  JiraCloud["Jira Cloud"]

  User --> CLI
  CLI --> Agent
  Agent --> Bedrock
  Agent --> Retriever
  Agent --> JiraAPI
  Retriever --> KnowledgeBase
  Bedrock -->|RAG| KnowledgeBase
  JiraAPI --> JiraCloud
```

## Flow Diagram

```mermaid
sequenceDiagram
  participant User
  participant CLI as CLI/Script
  participant Agent as Agent Logic
  participant Retriever
  participant Bedrock
  participant JiraAPI
  participant JiraCloud
  User->>CLI: Run with ticket key
  CLI->>Agent: main()
  Agent->>Bedrock: retrieve_and_generate()
  Bedrock->>Retriever: Retrieve context
  Retriever->>Bedrock: Return context
  Bedrock->>Agent: Generated comment
  Agent->>JiraAPI: add_comment()
  JiraAPI->>JiraCloud: POST comment
  JiraCloud-->>JiraAPI: Success
  JiraAPI-->>Agent: Success
  Agent-->>CLI: Print/Post result
  CLI-->>User: Show output
```

## Architecture
- **Python**: Orchestrates retrieval, generation, and JIRA API calls
- **AWS Bedrock**: Embedding, vector search, and LLM inference
- **Terraform**: Infrastructure as code for KB, data sources, IAM

## Setup
1. Clone the repo
2. Install Python dependencies: `pip install -r requirements.txt`
3. Configure AWS credentials and JIRA API access
4. Deploy infrastructure with Terraform (see kb.yaml, iam.yaml)
5. Set environment variables or edit `config.yaml` for runtime settings

## Usage
- Run the main script to generate and post JIRA comments:
  ```bash
  python jiraComment.py --ticket ABC-123
  ```
- Customize prompts, retrieval, and posting logic as needed

## Folder Structure
- `jiraComment.py` — Main script (to be modularized)
- `kb.yaml` — Bedrock KB and data source config
- `iam.yaml` — IAM policy for Bedrock, S3, OpenSearch, Secrets
- `requirements.txt` — Python dependencies
- `README.md` — This file

## Roadmap
- Modularize codebase (src/ or jirabot/)
- Add tests and CI
- Add Dockerfile and deployment scripts

## License
[MIT License](LICENSE)
