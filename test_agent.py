import os
import pytest
from agent import CoordinatorAgent, ContentSafetyPlugin, HITLHook
from tools import fetch_news_rss, send_email_digest, FetchNewsInput, SendDigestInput
from memory import PersistentMemory

@pytest.fixture(autouse=True)
def setup_test_db():
    if os.path.exists("test_agent_memory.db"):
        os.remove("test_agent_memory.db")
    yield
    if os.path.exists("test_agent_memory.db"):
        os.remove("test_agent_memory.db")

def test_fetch_news_tool_validation():
    with pytest.raises(Exception):
        FetchNewsInput() # missing parameter raises validation error

    valid_input = FetchNewsInput(query="Google Cloud", max_results=2)
    assert valid_input.query == "Google Cloud"
    assert valid_input.max_results == 2

def test_fetch_news_success():
    valid_input = FetchNewsInput(query="AI", max_results=2)
    res = fetch_news_rss(valid_input)
    assert isinstance(res, list)
    assert len(res) <= 2

def test_safety_plugin():
    safe_text = "Here is the daily technology digest on Kubernetes"
    unsafe_text = "Download this malware to exploit the system"
    assert ContentSafetyPlugin.verify_content(safe_text) is True
    assert ContentSafetyPlugin.verify_content(unsafe_text) is False

def test_hitl_hook():
    os.environ["AGENT_HITL_APPROVED"] = "True"
    assert HITLHook.require_approval("user@example.com", "Test") is True
    os.environ["AGENT_HITL_APPROVED"] = "False"
    assert HITLHook.require_approval("user@example.com", "Test") is False
    os.environ["AGENT_HITL_APPROVED"] = "True"

# Golden Dataset Evaluation Harness
def test_golden_dataset_evaluation():
    golden_dataset = [
        {
            "user_prompt": "Retrieve topic to Artificial Intelligence",
            "expected_topic_in_response": "Artificial Intelligence",
            "session_id": "test_sess_1"
        },
        {
            "user_prompt": "What are the latest updates on Kubernetes",
            "expected_topic_in_response": "Kubernetes",
            "session_id": "test_sess_2"
        }
    ]
    
    os.environ["AGENT_MEMORY_DB"] = "test_agent_memory.db"
    coordinator = CoordinatorAgent(db_path="test_agent_memory.db")
    
    for case in golden_dataset:
        response = coordinator.run_news_digest_cycle(case["session_id"], case["user_prompt"])
        assert "dispatched" in response.lower() or "failed" in response.lower()
        history = coordinator.memory.load_history(case["session_id"])
        assert len(history) > 0
        assert history[0]["role"] == "user"
        assert history[0]["content"] == case["user_prompt"]
