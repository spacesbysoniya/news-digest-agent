import feedparser
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from observability import setup_logger, trace_intent_outcome

logger = setup_logger("AgentTools")

class FetchNewsInput(BaseModel):
    query: str = Field(..., description="The keyword topic to search for, e.g., 'Google Cloud'")
    max_results: int = Field(default=3, description="Maximum number of news items to retrieve (must be between 1 and 5)")

class SendDigestInput(BaseModel):
    recipient_email: str = Field(..., description="The recipient's valid email address, e.g., 'soniyav@google.com'")
    subject: str = Field(..., description="The subject line of the email digest")
    body: str = Field(..., description="The formatted Markdown/text content of the news digest")

@trace_intent_outcome(logger)
def fetch_news_rss(input_data: FetchNewsInput) -> List[Dict[str, Any]]:
    """
    Fetches the latest news articles from Google News RSS feed for a specified topic keyword.
    
    Args:
        input_data (FetchNewsInput): The input schema containing:
            - query (str): The keyword or topic to search for on Google News.
            - max_results (int): The maximum number of news items to retrieve (default: 3).
            
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing news articles.
            
    Error Handling & Recovery:
        If fetching fails, the returned dictionary will contain an 'error' key with actionable recovery 
        instructions for the LLM. The LLM should attempt to retry once. If the query is too niche, 
        the LLM should retry with a broader query (e.g., 'Cloud Computing' instead of 'Vertex AI custom endpoint').
    """
    try:
        query = input_data.query
        max_results = input_data.max_results
        
        if not query:
            return [{"error": "The search query is empty. RECOVERY ACTION: Please prompt the user to provide a non-empty search keyword."}]
            
        encoded_query = query.replace(" ", "+")
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        
        results = []
        for entry in feed.entries[:max_results]:
            results.append({
                "title": entry.title,
                "link": entry.link,
                "published": getattr(entry, "published", "N/A")
            })
        if not results:
            return [{
                "error": f"No articles found for topic: '{query}'. "
                         f"RECOVERY ACTION: The search returned 0 results. Try retrying with a broader, "
                         f"more common keyword related to the user's intent."
            }]
        return results
    except Exception as e:
        return [{
            "error": f"Failed to fetch news RSS due to network/parsing error: {str(e)}. "
                     f"RECOVERY ACTION: Please check if the query uses special characters, retry once, "
                     f"or inform the user of a temporary service disruption and offer to read cached favorites."
        }]

@trace_intent_outcome(logger)
def send_email_digest(input_data: SendDigestInput) -> Dict[str, Any]:
    """
    Dispatches the formatted news digest via email.
    
    Args:
        input_data (SendDigestInput): The input schema containing:
            - recipient_email (str): Target user email address.
            - subject (str): Subject line of the email.
            - body (str): Formatted Markdown/Text body of the news digest.
            
    Returns:
        Dict[str, Any]: A dictionary showing the delivery status.
            
    Error Handling & Recovery:
        If sending fails (e.g., due to an invalid email format), it returns an error with recovery actions.
        The LLM should prompt the user to verify and correct their email address.
    """
    try:
        recipient = input_data.recipient_email
        subject = input_data.subject
        body = input_data.body
        
        if "@" not in recipient or "." not in recipient:
            return {
                "status": "failed",
                "error": f"Invalid email format: '{recipient}'. "
                         f"RECOVERY ACTION: The email format is invalid. Prompt the user for a correct email address, "
                         f"then retry dispatching."
            }
            
        print(f"\n--- [DISPATCHING EMAIL] ---")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print(f"---------------------------\n")
        
        return {
            "status": "success",
            "message": f"Digest successfully dispatched to {recipient}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Email service offline: {str(e)}. "
                     f"RECOVERY ACTION: Check network connectivity, wait 5 seconds, and retry. "
                     f"If failure persists, write the digest output directly into the chat response instead."
        }