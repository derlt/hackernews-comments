import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .api import fetch_comments
from .storage import Storage
from .threads import generate_threads

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "threads":
        _run_threads()
    elif len(sys.argv) > 1 and sys.argv[1] == "migrate":
        _run_migrate()
    else:
        _run_download()


def _run_download() -> None:
    parser = argparse.ArgumentParser(
        description="Download Hacker News comments from a date onward"
    )
    parser.add_argument(
        "--start-date", required=True, help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", help="End date (YYYY-MM-DD, default: now)"
    )
    parser.add_argument(
        "--output-dir",
        default="./hn_data",
        type=Path,
        help="Output directory (default: ./hn_data)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Requests per second (default: 1.0)",
    )
    parser.add_argument(
        "--db-name",
        default="comments.db",
        help="SQLite database filename (default: comments.db)",
    )
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    start_ts = int(start_dt.timestamp())

    end_ts: int | None = None
    if args.end_date:
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        end_ts = int((end_dt + timedelta(days=1)).timestamp())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    storage = Storage(args.output_dir, args.db_name)

    max_ts = storage.get_max_timestamp()
    if max_ts is not None and max_ts > start_ts:
        day_start = int(
            datetime.fromtimestamp(max_ts, tz=timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        if end_ts is not None and day_start >= end_ts:
            logger.info("all data already fetched")
            return
        start_ts = day_start
        logger.info("resuming from day-start timestamp %s", start_ts)

    total = 0
    try:
        for batch in fetch_comments(start_ts, end_ts, args.rate_limit):
            storage.save_comments(batch)
            total += len(batch)
            logger.info("saved %d comments (total: %d)", len(batch), total)
    except KeyboardInterrupt:
        logger.info("interrupted after %d comments", total)
    finally:
        storage.close()


def _run_threads() -> None:
    parser = argparse.ArgumentParser(description="Generate thread-grouped markdown")
    parser.add_argument(
        "--output-dir",
        default="./hn_data",
        type=Path,
        help="Output directory with comments.db (default: ./hn_data)",
    )
    parser.add_argument(
        "--db-name",
        default="comments.db",
        help="SQLite database filename (default: comments.db)",
    )
    args = parser.parse_args(sys.argv[2:])
    logger.info("generating threads...")
    generate_threads(args.output_dir, args.db_name)
    logger.info("done")


def _run_migrate() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate markdown from SQLite in new format"
    )
    parser.add_argument(
        "--output-dir",
        default="./hn_data",
        type=Path,
        help="Output directory with comments.db (default: ./hn_data)",
    )
    parser.add_argument(
        "--db-name",
        default="comments.db",
        help="SQLite database filename (default: comments.db)",
    )
    args = parser.parse_args(sys.argv[2:])
    _run_migrate_impl(args.output_dir, args.db_name)


def _run_migrate_impl(output_dir: Path, db_name: str) -> None:
    import sqlite3

    from .storage import Storage, _html_to_text

    db_path = output_dir / db_name
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute("""
        SELECT id, author, text, created_at, parent_id, story_id
        FROM comments
        ORDER BY created_at_i
    """)

    storage = Storage(output_dir, db_name)
    markdown_dir = output_dir / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)

    for filepath in markdown_dir.glob("*.md"):
        filepath.unlink()

    from collections import defaultdict
    from .models import HNComment

    batch_size = 1000
    batch = []
    total = 0

    for row in cur:
        batch.append(
            HNComment(
                id=str(row[0]),
                author=row[1],
                text=row[2],
                created_at=row[3],
                created_at_i=0,
                parent_id=row[4],
                story_id=row[5],
                url=f"https://news.ycombinator.com/item?id={row[0]}",
            )
        )
        if len(batch) >= batch_size:
            storage._save_markdown(batch)
            total += len(batch)
            logger.info("migrated %d comments", total)
            batch.clear()

    if batch:
        storage._save_markdown(batch)
        total += len(batch)

    conn.close()
    storage.close()
    logger.info("migration complete: %d comments to markdown", total)

    logger.info("generating threads...")
    generate_threads(output_dir, db_name)
    logger.info("threads done")
