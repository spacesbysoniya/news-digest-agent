import feedparser
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class FetchNewsInput(BaseModel):
    query: str = Field(description="Topic keyword to search for, e.g., 'Artificial Intelligence'")
    max_results: int = Field(default=3, description="Maximum number of news items to retrieve (1-5)")

class NewsItem(BaseModel):
    title: str
    link: str
    published: str

def fetch_news_rss(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Fetches recent news articles from an RSS feed for a given keyword topic."""
    try:
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
        return results if results else [{"error": f"No news found for topic: {query}"}]
    except Exception as e:
        return [{"error": f"Failed to fetch news RSS: {str(e)}"}]

class SendDigestInput(BaseModel):
    recipient_email: str = Field(description="Target user email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Formatted Markdown/Text content of the news digest")

def send_email_digest(recipient_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Simulates dispatching the final formatted news digest to the user's email."""
    # Production implementation would integrate with SendGrid, Gmail API, or SMTP
    print(f"\n--- [DISPATCHING EMAIL] ---")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}\n---------------------------\n")
    return {"status": "success", "message": f"Digest successfully dispatched to {recipient_email}"}
