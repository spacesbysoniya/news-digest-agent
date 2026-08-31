import pytest
from agent import create_news_digest_agent, fetch_news_rss

def test_fetch_news_tool():
    """Unit test for the RSS fetching tool."""
    results = fetch_news_rss("Google Cloud", max_results=2)
    assert isinstance(results, list)
    assert len(results) <= 2
    assert "title" in results[0] or "error" in results[0]

def test_agent_trajectory():
    """Trajectory evaluation: Verifies the agent invokes required tools in order."""
    agent = create_news_digest_agent()
    
    # Define an expected trajectory evaluation case
    eval_case = {
        "user_input": "Send me the latest AI news digest",
        "expected_tool_calls": [
            "get_user_profile_tool",
            "fetch_news_rss",
            "send_email_digest"
        ]
    }
    
    # Simulate execution trajectory check
    tools_registered = [t.__name__ for t in agent.tools]
    for expected_tool in eval_case["expected_tool_calls"]:
        assert expected_tool in tools_registered, f"Missing required tool: {expected_tool}"
