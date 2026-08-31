from typing import Dict, Optional

class UserPreferenceMemory:
    """Manages long-term user preferences across separate sessions."""
    def __init__(self):
        self._db: Dict[str, Dict[str, str]] = {
            "user_default": {
                "email": "user@example.com",
                "default_topic": "Artificial Intelligence",
                "digest_format": "bullet_points"
            }
        }

    def get_preferences(self, user_id: str = "user_default") -> Dict[str, str]:
        """Retrieves persistent user preferences like preferred email and topics."""
        return self._db.get(user_id, {
            "email": "unknown@example.com",
            "default_topic": "Technology",
            "digest_format": "bullet_points"
        })

    def update_topic(self, new_topic: str, user_id: str = "user_default") -> None:
        """Updates the default topic stored in memory."""
        if user_id in self._db:
            self._db[user_id]["default_topic"] = new_topic
