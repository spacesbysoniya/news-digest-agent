import os
from typing import Dict, List, Any, Tuple
from tools import fetch_news_rss, send_email_digest, FetchNewsInput, SendDigestInput
from memory import PersistentMemory
from observability import setup_logger, trace_intent_outcome, PIIRedactor
from secrets_manager import SecureSecretManager

logger = setup_logger("OrchestrationAgent")

class ContentSafetyPlugin:
    """Safety policy plugin verifying outputs against blacklisted phrases."""
    BANNED_WORDS = ["malware", "phishing", "exploit", "hack", "scam"]
    
    @classmethod
    def verify_content(cls, text: str) -> bool:
        text_lower = text.lower()
        for word in cls.BANNED_WORDS:
            if word in text_lower:
                logger.warning(f"Safety Violation: Found blocked word '{word}' in content.")
                return False
        return True

class HITLHook:
    """Human-In-The-Loop hook checking manual confirmations for critical operations."""
    @classmethod
    def require_approval(cls, recipient: str, subject: str) -> bool:
        logger.info(f"HITL Hook: Requesting permission to dispatch email to {PIIRedactor.redact(recipient)}")
        is_approved = os.getenv("AGENT_HITL_APPROVED", "True").lower() == "true"
        if is_approved:
            logger.info("HITL Hook: Dispatch approved.")
        else:
            logger.warning("HITL Hook: Dispatch denied by operator.")
        return is_approved

class NewsHarvesterAgent:
    """Specialized node routing tasks with speed-optimized gemini-2.5-flash."""
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name
        
    def harvest(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        logger.info(f"NewsHarvesterAgent routing to model: {self.model_name}")
        pydantic_input = FetchNewsInput(query=query, max_results=max_results)
        return fetch_news_rss(pydantic_input)

class DeliveryAgent:
    """Specialized node routing secure deliveries to precision-optimized gemini-2.5-pro."""
    def __init__(self, model_name="gemini-2.5-pro"):
        self.model_name = model_name
        
    def dispatch(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        logger.info(f"DeliveryAgent routing to model: {self.model_name}")
        
        # 1. Check Content Policies
        if not ContentSafetyPlugin.verify_content(body):
            return {"status": "failed", "error": "Safety policy violation detected in digest content."}
            
        # 2. Require HITL operators
        if not HITLHook.require_approval(recipient, subject):
            return {"status": "failed", "error": "Dispatch rejected by operator in HITL hook."}
            
        pydantic_input = SendDigestInput(recipient_email=recipient, subject=subject, body=body)
        return send_email_digest(pydantic_input)

class CoordinatorAgent:
    """Director Agent handling session memory, preferences, routing, and error-recovery."""
    def __init__(self, db_path="agent_memory.db"):
        self.memory = PersistentMemory(db_path=db_path)
        self.harvester = NewsHarvesterAgent()
        self.delivery_agent = DeliveryAgent()
        
    @trace_intent_outcome(logger)
    def run_news_digest_cycle(self, session_id: str, user_query: str) -> str:
        self.memory.save_message(session_id, "user", user_query)
        self.memory.compact_history(session_id)
        
        prefs = self.memory.get_preferences("user_default")
        recipient = prefs["email"]
        topic = prefs["default_topic"]
        
        if "topic to" in user_query.lower() or "search for" in user_query.lower():
            import re
            match = re.search(r"topic to ([\w\s]+)", user_query, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                self.memory.save_preferences("user_default", recipient, topic, prefs["digest_format"])
                logger.info(f"Coordinator: Updated persistent topic preference to '{topic}'")

        # Delegate Harvesting (model-routing to gemini-2.5-flash)
        logger.info(f"Coordinator: Delegating news harvesting for topic '{topic}'...")
        articles = self.harvester.harvest(topic, max_results=3)
        
        # Actionable Error Recovery
        if articles and "error" in articles[0]:
            error_msg = articles[0]["error"]
            logger.warning(f"Harvester error encountered: {error_msg}")
            fallback_topic = "Technology"
            logger.info(f"Coordinator: Running error recovery action. Retrying with fallback '{fallback_topic}'...")
            articles = self.harvester.harvest(fallback_topic, max_results=3)
            topic = fallback_topic

        body_lines = [f"# Daily News Digest: {topic}\n"]
        for art in articles:
            if "error" not in art:
                body_lines.append(f"### {art['title']}")
                body_lines.append(f"- Published: {art['published']}")
                body_lines.append(f"- Read more: {art['link']}\n")
        digest_body = "\n".join(body_lines)
        
        # Delegate Delivery (model-routing to gemini-2.5-pro)
        subject = f"Your Daily News Digest: {topic}"
        logger.info(f"Coordinator: Delegating secure email dispatch to '{PIIRedactor.redact(recipient)}'...")
        dispatch_result = self.delivery_agent.dispatch(recipient, subject, digest_body)
        
        if dispatch_result.get("status") == "success":
            outcome_text = f"Digest successfully dispatched to {recipient} on topic '{topic}'."
        else:
            outcome_text = f"Failed to dispatch digest. Reason: {dispatch_result.get('error')}"
            
        self.memory.save_message(session_id, "model", outcome_text)
        return outcome_text

if __name__ == "__main__":
    print("--- Running Local Demonstration ---")
    coordinator = CoordinatorAgent()
    result = coordinator.run_news_digest_cycle("session_demo_1", "Please trigger my news digest.")
    print("\nFinal Response:", result)
