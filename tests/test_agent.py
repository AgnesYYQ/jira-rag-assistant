from jirabot import agent

def test_system_prompt():
    prompt = agent.get_system_prompt()
    assert "Senior Project Assistant" in prompt
    assert "Jira ticket" in prompt
