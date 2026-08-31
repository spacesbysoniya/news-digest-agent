import os
import logging
from google.cloud import agent_tooling  # ADK SDK
from tools import fetch_news_rss, send_email_digest
from memory import UserPreferenceMemory

# Setting up Observability & Tracing via Standard Logging / Cloud Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("NewsDigestAgent")

memory_store = UserPreferenceMemory()

def get_user_profile_tool() -> dict:
    """Tool to read persistent user profile and topic preferences from memory."""
    logger.info("Executing Tool: get_user_profile_tool")
    return memory_store.get_preferences()

SYSTEM_INSTRUCTION = """
You are an autonomous Daily News Digest Agent. Your goal is to deliver a concise news summary.

Follow this exact orchestration trajectory:
1. Call `get_user_profile_tool` to retrieve the user's email and topic preferences if not provided by the user.
2. Call `fetch_news_rss` with the topic keyword to get the top 3 news items.
3. Synthesize and format the retrieved articles into a clean Markdown summary. Each entry must include:
   - Article Title
   - Key takeaway summary (1 sentence)
   - Link URL
4. Call `send_email_digest` to dispatch the summary to the user's email address.
5. Provide a final response confirming that the news digest has been dispatched.
"""

def create_news_digest_agent():
    """Initializes the Agent using ADK abstractions."""
    agent = agent_tooling.Agent(
        model="gemini-2.5-flash",
        instructions=SYSTEM_INSTRUCTION,
        tools=[
            get_user_profile_tool,
            fetch_news_rss,
            send_email_digest
        ]
    )
    return agent

# Agent Execution Entry Point with Trajectory Callbacks
def run_agent_turn(user_query: str, session_state: dict = None):
    logger.info(f"Starting Agent Turn | Input Query: '{user_query}'")
    agent = create_news_digest_agent()
    
    # Execute the agent logic
    response = agent.run(user_query, session_state=session_state)
    
    logger.info("Agent Turn Completed Successfully")
    return response

if __name__ == "__main__":
    print("--- Running Local Test of News Digest Agent ---")
    output = run_agent_turn("Generate my news digest for today.")
    print(output)
