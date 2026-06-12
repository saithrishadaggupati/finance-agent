import sqlite3
from datetime import datetime
from app.models.schemas import MemoryItem
from app.core.config import get_settings


class MemoryStore:
    def __init__(self):
        self.settings = get_settings()
        self.db_path = self.settings.memory_db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    context TEXT
                )
            """)
            conn.commit()

    def save(self, question: str, answer: str, context: str = "") -> MemoryItem:
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO memory (question, answer, timestamp, context) VALUES (?, ?, ?, ?)",
                (question, answer, timestamp, context)
            )
            conn.commit()
            return MemoryItem(
                id=cursor.lastrowid,
                question=question,
                answer=answer,
                timestamp=timestamp,
                context=context
            )

    def get_recent(self, limit: int = 5) -> list[MemoryItem]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, question, answer, timestamp, context FROM memory ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [
                MemoryItem(
                    id=row[0],
                    question=row[1],
                    answer=row[2],
                    timestamp=row[3],
                    context=row[4]
                )
                for row in rows
            ]

    def format_for_prompt(self, limit: int = 3) -> str:
        items = self.get_recent(limit)
        if not items:
            return "No previous context."
        parts = []
        for item in reversed(items):
            parts.append(f"Q: {item.question}\nA: {item.answer}")
        return "\n\n".join(parts)

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory")
            conn.commit()


def get_memory_store() -> MemoryStore:
    return MemoryStore()