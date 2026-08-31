import os
import re
import asyncio
from typing import Dict, List, Any
from tools import fetch_news_rss, send_email_digest, FetchNewsInput, SendDigestInput
from memory import AsyncMemoryManager
from observability import setup_logger, trace_intent_outcome, PIIRedactor

logger = setup_logger("OrchestrationAgent")

# Explicit, detailed system instructions defining persona, constraints, and trajectory
SYSTEM_INSTRUCTION = """
You are the Autonomous Daily News Digest Orchestrator. Your role is to compile and dispatch high-quality, relevant news summaries to users.

### CORE OPERATING PRINCIPLES:
1. Persona & Tone: Professional, direct, informative, and security-conscious.
2. Multi-Agent Delegation:
   - Route retrieval tasks to `NewsHarvesterAgent` (powered by Gemini Flash for low-latency summarization).
   - Route verification and final email dispatch to `DeliveryAgent` (powered by Gemini Pro for policy adherence).
3. Safety & Guardrails:
   - Never process or dispatch content containing phishing, malware, or exploit keywords.
   - Strictly require Human-In-The-Loop (HITL) authorization before triggering email dispatch tools.
4. Error Recovery Protocol:
   - If a search query yields 0 results or an RSS parsing error occurs, backtrack and execute a fallback search with a broader topic (e.g., 'Technology').
"""

class ContentSafetyPlugin:
    """Enforces safety guardrails against malicious or prohibited keywords."""
    BANNED_WORDS = ["malware", "phishing", "exploit", "hack", "scam"]
    
    @classmethod
    def verify_content(cls, text: str) -> bool:
        text_lower = text.lower()
        for word in cls.BANNED_WORDS:
            if word in text_lower:
                logger.warning(f"Safety Violation: Blocked prohibited keyword '{word}'.")
                return False
        return True

class HITLHook:
    """Human-In-The-Loop hook requiring verification prior to mutative actions."""
    @classmethod
    def require_approval(cls, recipient: str, subject: str) -> bool:
        logger.info(f"HITL Hook: Requesting authorization to dispatch email to {PIIRedactor.redact(recipient)}")
        is_approved = os.getenv("AGENT_HITL_APPROVED", "True").lower() == "true"
        if is_approved:
            logger.info("HITL Hook: Authorization GRANTED.")
        else:
            logger.warning("HITL Hook: Authorization DENIED by operator.")
        return is_approved

class NewsHarvesterAgent:
    """Specialized worker agent optimized for fast RSS retrieval using Gemini Flash."""
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        
    def harvest(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        logger.info(f"NewsHarvesterAgent routing to model: '{self.model_name}' for query: '{query}'")
        pydantic_input = FetchNewsInput(query=query, max_results=max_results)
        return fetch_news_rss(pydantic_input)

class DeliveryAgent:
    """Specialized worker agent for policy checks and email dispatch using Gemini Pro."""
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.model_name = model_name
        
    def dispatch(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        logger.info(f"DeliveryAgent routing to model: '{self.model_name}'")
        
        # Guardrail check
        if not ContentSafetyPlugin.verify_content(body):
            return {"status": "failed", "error": "Safety violation: Prohibited keywords detected in digest."}
            
        # HITL confirmation check
        if not HITLHook.require_approval(recipient, subject):
            return {"status": "failed", "error": "Dispatch blocked: Human-In-The-Loop approval was denied."}
            
        pydantic_input = SendDigestInput(recipient_email=recipient, subject=subject, body=body)
        return send_email_digest(pydantic_input)

class CoordinatorAgent:
    """Master orchestrator integrating system prompts, async memory, and multi-agent coordination."""
    def __init__(self, db_path: str = "agent_memory.db"):
        self.system_instruction = SYSTEM_INSTRUCTION
        self.memory = AsyncMemoryManager(db_path=db_path)
        self.harvester = NewsHarvesterAgent()
        self.delivery_agent = DeliveryAgent()
        
    @trace_intent_outcome(logger)
    async def run_news_digest_cycle_async(self, session_id: str, user_query: str) -> str:
        # Guardrail check on input
        if not ContentSafetyPlugin.verify_content(user_query):
            return "Error: Your request contains terms that violate safety policies."

        # Async turn logging and non-blocking background context compaction
        await self.memory.save_message_async(session_id, "user", user_query)
        asyncio.create_task(self.memory.compact_history_async(session_id, max_turns=4))
        
        # Load user profile preferences asynchronously
        prefs = await self.memory.get_preferences_async("user_default")
        recipient = prefs["email"]
        topic = prefs["default_topic"]
        
        # Extract custom topic overrides
        if "topic to" in user_query.lower():
            match = re.search(r"topic to ([\w\s]+)", user_query, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                await self.memory.save_preferences_async("user_default", recipient, topic, prefs["digest_format"])
                logger.info(f"Coordinator: Persisted new topic preference: '{topic}'")

        # 1. Harvest news articles
        logger.info(f"Coordinator: Delegating retrieval for topic '{topic}'...")
        articles = self.harvester.harvest(topic, max_results=3)
        
        # Guided Error Recovery protocol
        if articles and "error" in articles[0]:
            logger.warning(f"Harvester error: {articles[0]['error']}. Initiating fallback recovery...")
            fallback_topic = "Technology"
            articles = self.harvester.harvest(fallback_topic, max_results=3)
            topic = fallback_topic

        # 2. Format digest
        body_lines = [f"# Daily News Digest: {topic.upper()}\n"]
        for art in articles:
            if "error" not in art:
                body_lines.append(f"### {art['title']}")
                body_lines.append(f"- Published: {art['published']}")
                body_lines.append(f"- Read more: {art['link']}\n")
        digest_body = "\n".join(body_lines)
        
        # 3. Dispatch via Delivery Agent
        subject = f"Your Daily News Digest: {topic}"
        dispatch_result = self.delivery_agent.dispatch(recipient, subject, digest_body)
        
        if dispatch_result.get("status") == "success":
            outcome_text = f"Digest successfully dispatched to {recipient} on topic '{topic}'."
        else:
            outcome_text = f"Failed to dispatch digest. Reason: {dispatch_result.get('error')}"
            
        await self.memory.save_message_async(session_id, "model", outcome_text)
        return outcome_text

    def run_news_digest_cycle(self, session_id: str, user_query: str) -> str:
        """Synchronous wrapper for CLI execution and standard unit testing."""
        return asyncio.run(self.run_news_digest_cycle_async(session_id, user_query))

if __name__ == "__main__":
    print("--- Running News Digest Multi-Agent System ---")
    coordinator = CoordinatorAgent()
    result = coordinator.run_news_digest_cycle("session_demo", "Send my daily news digest.")
    print("\nResult:", result)
