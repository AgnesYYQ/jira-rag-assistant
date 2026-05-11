

import pytest
from unittest.mock import patch, MagicMock
from jirabot.jira_api import JiraAPIWrapper

def test_jira_api_init():
    api = JiraAPIWrapper("https://example.com", "user", "token")
    assert api.api_url == "https://example.com"
    assert api.auth == ("user", "token")

@patch("jirabot.jira_api.requests.post")
def test_add_comment_success(mock_post):
    api = JiraAPIWrapper("https://example.com", "user", "token")
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "123"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    result = api.add_comment("ABC-123", "test comment")
    assert result == {"id": "123"}
    mock_post.assert_called_once_with(
        "https://example.com/rest/api/3/issue/ABC-123/comment",
        json={"body": "test comment"},
        auth=("user", "token")
    )

@patch("jirabot.jira_api.requests.post")
def test_add_comment_http_error(mock_post):
    api = JiraAPIWrapper("https://example.com", "user", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("fail")
    mock_post.return_value = mock_response
    with pytest.raises(Exception):
        api.add_comment("ABC-123", "test comment")
