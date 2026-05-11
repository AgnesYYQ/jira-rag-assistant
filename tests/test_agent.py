

import pytest
from unittest.mock import patch, MagicMock
from jirabot import agent

# Test config loading
@patch("builtins.open")
@patch("yaml.safe_load")
def test_load_config(mock_safe_load, mock_open):
    mock_safe_load.return_value = {"test": 1}
    config = agent.load_config("dummy.yaml")
    assert config == {"test": 1}
    mock_open.assert_called_once_with("dummy.yaml")

# Test Bedrock client creation
@patch("boto3.client")
def test_get_bedrock_client(mock_boto_client):
    agent.config["aws"] = {"region": "us-east-1"}
    client = MagicMock()
    mock_boto_client.return_value = client
    result = agent.get_bedrock_client()
    assert result is client
    mock_boto_client.assert_called_once_with("bedrock-agent-runtime", region_name="us-east-1")

# Test retriever creation
@patch("jirabot.agent.AmazonKnowledgeBasesRetriever")
def test_get_retriever(mock_retriever):
    agent.config["aws"] = {"bedrock_kb_id": "kb123"}
    agent.config["retriever"] = {"number_of_results": 5}
    instance = MagicMock()
    mock_retriever.return_value = instance
    result = agent.get_retriever()
    assert result is instance
    mock_retriever.assert_called_once()
    args, kwargs = mock_retriever.call_args
    assert kwargs["knowledge_base_id"] == "kb123"
    assert kwargs["retrieval_config"]["vectorSearchConfiguration"]["numberOfResults"] == 5

# Test Jira toolkit creation
@patch("jirabot.agent.JiraToolkit")
@patch("jirabot.jira_api.JiraAPIWrapper")
def test_get_jira_toolkit(mock_api_wrapper, mock_toolkit):
    agent.config["jira"] = {"api_url": "url", "username": "user", "api_token": "token"}
    api_instance = MagicMock()
    toolkit_instance = MagicMock()
    mock_api_wrapper.return_value = api_instance
    mock_toolkit.from_jira_api_wrapper.return_value = toolkit_instance
    result = agent.get_jira_toolkit()
    assert result is toolkit_instance
    mock_api_wrapper.assert_called_once_with(api_url="url", username="user", api_token="token")
    mock_toolkit.from_jira_api_wrapper.assert_called_once_with(api_instance)

# Test system prompt
def test_get_system_prompt():
    prompt = agent.get_system_prompt()
    assert "Senior Project Assistant" in prompt
    assert "Jira ticket" in prompt
