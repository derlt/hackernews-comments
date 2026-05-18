import time
from collections.abc import Iterator
from datetime import datetime, timezone

import httpx

from .models import HNComment

BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"
CHUNK_SIZE = 3600


def fetch_comments(
    start_ts: int,
    end_ts: int | None = None,
    rate_limit: float = 1.0,
) -> Iterator[list[HNComment]]:
    if end_ts is None:
        end_ts = int(datetime.now(timezone.utc).timestamp())

    client = httpx.Client(timeout=30.0)

    try:
        chunk_start = start_ts
        while chunk_start < end_ts:
            chunk_end = min(chunk_start + CHUNK_SIZE, end_ts)

            page = 0
            while True:
                params = {
                    "tags": "comment",
                    "numericFilters": (
                        f"created_at_i>{chunk_start},created_at_i<{chunk_end}"
                    ),
                    "hitsPerPage": 1000,
                    "page": page,
                }

                resp = _request_with_retry(client, params)
                data = resp.json()
                hits = data.get("hits", [])
                nb_pages = data.get("nbPages", 0)

                if not hits:
                    break

                yield [parse_hit(h) for h in hits]

                page += 1
                if page >= nb_pages:
                    break

                if rate_limit > 0:
                    time.sleep(1.0 / rate_limit)

            chunk_start = chunk_end

            if rate_limit > 0 and chunk_start < end_ts:
                time.sleep(1.0 / rate_limit)
    finally:
        client.close()


def _request_with_retry(
    client: httpx.Client,
    params: dict,
    retries: int = 3,
) -> httpx.Response:
    for attempt in range(retries):
        try:
            resp = client.get(BASE_URL, params=params)
            if resp.status_code == 429:
                raise httpx.HTTPStatusError(
                    "Rate limited", request=resp.request, response=resp
                )
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.ConnectError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))

    raise RuntimeError("unreachable")


def parse_hit(hit: dict) -> HNComment:
    return HNComment(
        id=str(hit["objectID"]),
        author=hit.get("author"),
        text=hit.get("comment_text"),
        created_at=hit["created_at"],
        created_at_i=hit["created_at_i"],
        parent_id=hit.get("parent_id"),
        story_id=hit.get("story_id"),
        url=hit.get("url")
        or f"https://news.ycombinator.com/item?id={hit['objectID']}",
    )
