from dataclasses import dataclass


@dataclass
class HNComment:
    id: str
    author: str | None
    text: str | None
    created_at: str
    created_at_i: int
    parent_id: int | None
    story_id: int | None
    url: str
