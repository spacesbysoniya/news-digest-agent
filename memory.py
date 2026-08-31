import sqlite3
import asyncio
from typing import Dict, List, Any
from observability import setup_logger, trace_intent_outcome

logger = setup_logger("PersistentMemory")

class PersistentMemory:
    """Manages long-term user preferences and conversation history using SQLite."""
    def __init__(self, db_path="agent_memory.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initializes tables for persistent user preferences and turn histories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    default_topic TEXT,
                    digest_format TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
    @trace_intent_outcome(logger)
    def get_preferences(self, user_id: str = "user_default") -> Dict[str, str]:
        """Retrieves persistent user profile preferences."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT email, default_topic, digest_format FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {"email": row[0], "default_topic": row[1], "digest_format": row[2]}
            else:
                self.save_preferences(user_id, "user@example.com", "Artificial Intelligence", "bullet_points")
                return {"email": "user@example.com", "default_topic": "Artificial Intelligence", "digest_format": "bullet_points"}
                
    @trace_intent_outcome(logger)
    def save_preferences(self, user_id: str, email: str, default_topic: str, digest_format: str) -> None:
        """Saves or updates user preferences in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences (user_id, email, default_topic, digest_format)
                VALUES (?, ?, ?, ?)
            """, (user_id, email, default_topic, digest_format))
            conn.commit()

    @trace_intent_outcome(logger)
    def load_history(self, session_id: str) -> List[Dict[str, str]]:
        """Loads chronological conversation history for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, content FROM conversation_history WHERE session_id = ? ORDER BY id ASC", (session_id,))
            return [{"role": r, "content": c} for r, c in cursor.fetchall()]

    @trace_intent_outcome(logger)
    def save_message(self, session_id: str, role: str, content: str) -> None:
        """Persists a single message turn."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_history (session_id, role, content)
                VALUES (?, ?, ?)
            """, (session_id, role, content))
            conn.commit()

    @trace_intent_outcome(logger)
    def compact_history(self, session_id: str, max_turns: int = 4) -> None:
        """Synchronous compaction logic that summarizes older turns into a unified context block."""
        history = self.load_history(session_id)
        if len(history) <= max_turns:
            return
            
        to_summarize = history[:-2]
        keep = history[-2:]
        summary_items = []
        for turn in to_summarize:
            role = turn["role"]
            content = turn["content"][:40] + "..." if len(turn["content"]) > 40 else turn["content"]
            summary_items.append(f"{role}: {content}")
        
        summary_content = "Summary of previous dialogue context: " + " | ".join(summary_items)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))
            conn.commit()
            
        self.save_message(session_id, "system", summary_content)
        for turn in keep:
            self.save_message(session_id, turn["role"], turn["content"])
            
        logger.info(f"History compacted for session '{session_id}'. Summarized {len(to_summarize)} turns.")

class AsyncMemoryManager:
    """Asynchronous wrapper ensuring database transactions and compaction run non-blockingly."""
    def __init__(self, db_path="agent_memory.db"):
        self.sync_memory = PersistentMemory(db_path)
        
    async def get_preferences_async(self, user_id: str = "user_default") -> Dict[str, str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.sync_memory.get_preferences, user_id)
        
    async def save_preferences_async(self, user_id: str, email: str, default_topic: str, digest_format: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.sync_memory.save_preferences, user_id, email, default_topic, digest_format)

    async def save_message_async(self, session_id: str, role: str, content: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.sync_memory.save_message, session_id, role, content)

    async def compact_history_async(self, session_id: str, max_turns: int = 4) -> None:
        """Executes context compaction asynchronously as a background task."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.sync_memory.compact_history, session_id, max_turns)
