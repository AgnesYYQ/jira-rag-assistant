from jirabot.jira_api import JiraAPIWrapper

def test_jira_api_init():
    api = JiraAPIWrapper("https://example.com", "user", "token")
    assert api.api_url == "https://example.com"
    assert api.auth == ("user", "token")
