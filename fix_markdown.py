#!/usr/bin/env python3
"""Fix existing markdown files to only keep comment_id and comment text."""

from pathlib import Path
import sys


def fix_markdown_file(filepath: Path) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # First non-blank line in a block is the metadata line
        parts = stripped.split(maxsplit=1)
        comment_id = parts[0] if parts else ""

        # The next line(s) until a blank line form the comment text
        i += 1
        comment_lines: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            comment_lines.append(lines[i])
            i += 1

        # Skip any following blank lines to find the next block
        while i < len(lines) and lines[i].strip() == "":
            i += 1

        comment_text = "".join(comment_lines).rstrip("\n")
        out_lines.append(f"{comment_id}\n")
        out_lines.append(f"{comment_text}\n")
        out_lines.append("\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"Fixed {filepath}")


def main() -> None:
    markdown_dir = Path("./hn_data/markdown")
    if not markdown_dir.exists():
        print(f"Directory not found: {markdown_dir}", file=sys.stderr)
        sys.exit(1)

    for md_file in sorted(markdown_dir.glob("*.md")):
        fix_markdown_file(md_file)


if __name__ == "__main__":
    main()
