from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from .storage import _html_to_text

_MAX_DEPTH = 6


def generate_threads(output_dir: Path, db_name: str = "comments.db") -> None:
    db_path = output_dir / db_name
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cur = conn.execute("""
        SELECT id, author, text, created_at, created_at_i, parent_id, story_id
        FROM comments
        ORDER BY story_id, created_at_i
    """)

    stories: dict[int, _StoryData] = {}

    for row in cur:
        sid = row["story_id"]
        cid = row["id"]
        pid = row["parent_id"]

        if sid not in stories:
            stories[sid] = _StoryData()

        comment = _Comment(
            id=cid,
            author=row["author"] or "[deleted]",
            text=_html_to_text(row["text"] or ""),
            date=row["created_at"][:10],
            created_at_i=row["created_at_i"],
            parent_id=pid,
        )
        stories[sid].comments[cid] = comment

    for sid, data in stories.items():
        for cid, c in data.comments.items():
            pid = c.parent_id
            if pid == sid:
                data.roots.append(cid)
            elif str(pid) in data.comments:
                data.children[str(pid)].append(cid)
            else:
                data.orphans.append(cid)

        data.roots.sort(key=lambda cid: data.comments[cid].created_at_i)
        data.orphans.sort(key=lambda cid: data.comments[cid].created_at_i)
        for p in data.children:
            data.children[p].sort(key=lambda cid: data.comments[cid].created_at_i)

    threads_dir = output_dir / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)

    for sid, data in stories.items():
        filepath = threads_dir / f"{sid}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# story:{sid}\n\n")
            for cid in data.roots:
                _write_comment(f, data, cid, depth=0)

    conn.close()


def _write_comment(f, data: _StoryData, cid: str, depth: int) -> None:
    comment = data.comments[cid]
    level = min(depth + 2, _MAX_DEPTH)
    heading = "#" * level

    f.write(f"{heading} {cid} | {comment.author} | {comment.date}\n")
    if depth > 0:
        f.write(f"> reply to {comment.parent_id}\n\n")
    else:
        f.write("\n")
    f.write(f"{comment.text}\n\n")

    for child_cid in data.children.get(cid, []):
        _write_comment(f, data, child_cid, depth + 1)


class _Comment:
    __slots__ = ("id", "author", "text", "date", "created_at_i", "parent_id")

    def __init__(
        self,
        id: str,
        author: str,
        text: str,
        date: str,
        created_at_i: int,
        parent_id: int,
    ):
        self.id = id
        self.author = author
        self.text = text
        self.date = date
        self.created_at_i = created_at_i
        self.parent_id = parent_id


class _StoryData:
    __slots__ = ("comments", "children", "roots", "orphans")

    def __init__(self):
        self.comments: dict[str, _Comment] = {}
        self.children: dict[str, list[str]] = defaultdict(list)
        self.roots: list[str] = []
        self.orphans: list[str] = []
