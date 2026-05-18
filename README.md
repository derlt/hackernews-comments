# Hacker News Comment Downloader

Download all HN comments from a given date onward via the Algolia API.

## Usage

```bash
uv run python -m hackernews_comments --start-date 2026-05-01 --output-dir ./data
```

## Arguments

| Argument       | Default     | Description               |
| -------------- | ----------- | ------------------------- |
| `--start-date` | required    | Start date (YYYY-MM-DD)   |
| `--end-date`   | now         | End date (YYYY-MM-DD)     |
| `--output-dir` | `./hn_data` | Output directory          |
| `--rate-limit` | `1.0`       | Requests per second       |
| `--db-name`    | `comments.db` | SQLite database filename |

## Output

- **SQLite** — `comments.db` with `INSERT OR IGNORE` for idempotent resumption
- **Markdown** — `markdown/YYYY-MM-DD.md` files with one compact header line per comment

Read more in [PLAN.md](./PLAN.md).
