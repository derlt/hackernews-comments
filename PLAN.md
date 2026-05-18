# Hacker News Comment Downloader

## Objective

A reusable Python CLI tool that downloads Hacker News comments from a given
start date onward, persists them to SQLite, and exports them to compact
Markdown for AI agent consumption.

## Usage

```bash
uv run python -m hackernews_comments --start-date 2025-01-01 --output-dir ./data
```

### Arguments

| Argument       | Required | Default     | Description                     |
| -------------- | -------- | ----------- | ------------------------------- |
| `--start-date` | yes      | —           | Start date (YYYY-MM-DD)         |
| `--end-date`   | no       | now         | End date (YYYY-MM-DD)           |
| `--output-dir` | no       | `./hn_data` | Output directory                |
| `--rate-limit` | no       | `1.0`       | Requests per second             |
| `--db-name`    | no       | `comments.db` | SQLite database filename      |

## Architecture

```
src/hackernews_comments/
├── __init__.py   # re-exports main()
├── __main__.py   # entry point for `python -m`
├── main.py       # CLI argument parsing & orchestration
├── api.py        # Algolia client, pagination, retries, rate limits
├── models.py     # HNComment dataclass
└── storage.py    # SQLite & Markdown writers
```

## Data Flow

1. Parse CLI args, convert `--start-date` to Unix timestamp.
2. Check SQLite for latest `created_at_i` — resume from there to avoid
   re-downloading already-saved data.
3. Call Algolia `search_by_date` API (`tags=comment`,
   `numericFilters=created_at_i>=...`), paginate 1000 hits per page.
4. Each batch of up to 1000 comments is saved to SQLite (`INSERT OR IGNORE`
   for idempotency) and appended to the correct
   `markdown/YYYY-MM-DD.md` file.
5. Enforce configurable rate limit between pagination requests. Retry up to
   3 times with exponential backoff on HTTP 429 or network errors.

## API

**Endpoint:** `https://hn.algolia.com/api/v1/search_by_date`

**Rate limit:** Default 1 req/s, configurable via `--rate-limit`.

**Pagination limit:** Algolia caps results at ~1000 pages. The tool stops
cleanly with a warning when this ceiling is reached. For very large
historical backfills, date-range chunking can be added in a future version.

## Output

### SQLite (`output_dir/comments.db`)

| Column       | Type    | Description                     |
| ------------ | ------- | ------------------------------- |
| `id`         | TEXT PK | Algolia objectID                |
| `author`     | TEXT    | Comment author                  |
| `text`       | TEXT    | Raw HTML comment text           |
| `created_at` | TEXT    | ISO 8601 timestamp              |
| `created_at_i` | INTEGER | Unix timestamp                |
| `parent_id`  | INTEGER | Parent comment or story ID      |
| `story_id`   | INTEGER | Root story ID                   |
| `url`        | TEXT    | Permalink to comment            |
| `fetched_at` | TEXT    | Ingestion timestamp (auto)      |

### Markdown (`output_dir/markdown/YYYY-MM-DD.md`)

Token-minimized format — one header line per comment followed by text:

```
<id> <author> <created_at> p=<parent_id> s=<story_id> <url>
<comment text>

<id> <author> <created_at> p=<parent_id> s=<story_id> <url>
<comment text>
...
```

## Development

```bash
uv run python -m hackernews_comments --help
uv run python -m hackernews_comments --start-date 2026-05-18 --output-dir /tmp/hn_test
```
