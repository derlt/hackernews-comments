import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .api import fetch_comments
from .storage import Storage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
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
