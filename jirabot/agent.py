"""
Agent logic for JiraBot: retrieval, generation, and JIRA comment posting.
"""
import os
import yaml
import boto3
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.agent_toolkits import JiraToolkit
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

# Load config
def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

config = load_config()

# Setup Bedrock client
def get_bedrock_client():
    return boto3.client("bedrock-agent-runtime", region_name=config['aws']['region'])

# Setup retriever
def get_retriever():
    return AmazonKnowledgeBasesRetriever(
        knowledge_base_id=config['aws']['bedrock_kb_id'],
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": config['retriever']['number_of_results']}}
    )

# Setup Jira toolkit
def get_jira_toolkit():
    # You should implement JiraAPIWrapper to wrap authentication and API calls
    from .jira_api import JiraAPIWrapper
    jira_api_wrapper = JiraAPIWrapper(
        api_url=config['jira']['api_url'],
        username=config['jira']['username'],
        api_token=config['jira']['api_token']
    )
    return JiraToolkit.from_jira_api_wrapper(jira_api_wrapper)

# System prompt
def get_system_prompt():
    return (
        "You are a Senior Project Assistant. Your workflow:\n"
        "1. Analyze the current Jira ticket.\n"
        "2. Use the Knowledge Base to find related wiki pages and previous tickets.\n"
        "3. Draft a suggestion that cites sources like [Wiki: Page Name] or [Jira: ABC-123].\n"
        "4. Post the comment to the ticket if the confidence is high."
    )
