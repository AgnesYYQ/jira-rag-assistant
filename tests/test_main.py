

import pytest
import sys
from jirabot import main
from unittest.mock import patch, MagicMock

@patch("jirabot.main.get_bedrock_client")
@patch("jirabot.main.get_retriever")
@patch("jirabot.main.get_jira_toolkit")
@patch("jirabot.main.get_system_prompt")
def test_main_dry_run(mock_prompt, mock_jira_toolkit, mock_retriever, mock_bedrock_client, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['main.py', '--ticket', 'ABC-123', '--dry-run'])
    monkeypatch.setattr('builtins.print', lambda *a, **k: None)
    mock_bedrock = MagicMock()
    mock_bedrock.retrieve_and_generate.return_value = {'output': {'text': 'comment'}}
    mock_bedrock_client.return_value = mock_bedrock
    mock_jira_toolkit.return_value = MagicMock(get_tools=lambda: [MagicMock(add_comment=MagicMock())])
    try:
        main.main()
    except SystemExit:
        pass

@patch("jirabot.main.get_bedrock_client")
@patch("jirabot.main.get_retriever")
@patch("jirabot.main.get_jira_toolkit")
@patch("jirabot.main.get_system_prompt")
def test_main_post_comment(mock_prompt, mock_jira_toolkit, mock_retriever, mock_bedrock_client, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['main.py', '--ticket', 'ABC-123'])
    monkeypatch.setattr('builtins.print', lambda *a, **k: None)
    mock_bedrock = MagicMock()
    mock_bedrock.retrieve_and_generate.return_value = {'output': {'text': 'comment'}}
    mock_bedrock_client.return_value = mock_bedrock
    mock_tool = MagicMock()
    mock_jira_toolkit.return_value = MagicMock(get_tools=lambda: [mock_tool])
    try:
        main.main()
    except SystemExit:
        pass
    mock_tool.add_comment.assert_called_once_with('ABC-123', 'comment')
