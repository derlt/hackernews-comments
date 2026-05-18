import sqlite3
from collections import defaultdict
from pathlib import Path

from .models import HNComment


class Storage:
    def __init__(self, output_dir: Path, db_name: str = "comments.db"):
        self.markdown_dir = output_dir / "markdown"
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = output_dir / db_name
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                author TEXT,
                text TEXT,
                created_at TEXT,
                created_at_i INTEGER,
                parent_id INTEGER,
                story_id INTEGER,
                url TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_time ON comments(created_at_i)"
        )
        self.conn.commit()

    def save_comments(self, comments: list[HNComment]) -> None:
        self._save_sqlite(comments)
        self._save_markdown(comments)

    def _save_sqlite(self, comments: list[HNComment]) -> None:
        rows = [
            (
                c.id,
                c.author,
                c.text,
                c.created_at,
                c.created_at_i,
                c.parent_id,
                c.story_id,
                c.url,
            )
            for c in comments
        ]
        self.conn.executemany(
            """INSERT OR IGNORE INTO comments
               (id, author, text, created_at, created_at_i, parent_id, story_id, url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        self.conn.commit()

    def _save_markdown(self, comments: list[HNComment]) -> None:
        grouped: dict[str, list[HNComment]] = defaultdict(list)
        for c in comments:
            date_str = c.created_at[:10]
            grouped[date_str].append(c)

        for date_str, group in grouped.items():
            filepath = self.markdown_dir / f"{date_str}.md"
            with open(filepath, "a", encoding="utf-8") as f:
                for c in group:
                    pid = c.parent_id if c.parent_id is not None else ""
                    sid = c.story_id if c.story_id is not None else ""
                    f.write(
                        f"{c.id} {c.author} {c.created_at} p={pid} s={sid} {c.url}\n"
                    )
                    f.write(f"{c.text or ''}\n\n")

    def get_max_timestamp(self) -> int | None:
        cursor = self.conn.execute("SELECT MAX(created_at_i) FROM comments")
        return cursor.fetchone()[0]

    def close(self) -> None:
        self.conn.close()
