"""
Jira API Wrapper for authentication and basic operations.
"""
import requests

class JiraAPIWrapper:
    def __init__(self, api_url, username, api_token):
        self.api_url = api_url.rstrip('/')
        self.auth = (username, api_token)

    def add_comment(self, issue_key, comment):
        url = f"{self.api_url}/rest/api/3/issue/{issue_key}/comment"
        resp = requests.post(url, json={"body": comment}, auth=self.auth)
        resp.raise_for_status()
        return resp.json()

    # Add more methods as needed (get_issue, search_issues, etc.)
