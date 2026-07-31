#!/usr/bin/env python3
"""Turn a submitted "Add a book" issue into a book page.

GitHub renders an issue form as markdown: one `### <label>` heading per field,
the answer underneath, `_No response_` where the field was left blank, and
`- [x] Tag` lines for checkboxes. This reads that back, maps it onto the
frontmatter fields `scripts/shelves.py` expects, and writes `docs/<slug>.md`.

Only frontmatter and notes are written — the heading, the metadata card and
every listing that mentions the book come from `scripts/shelves.py`, which the
workflow runs straight afterwards.

Usage: python3 scripts/add_book.py <issue-body-file>
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

SHELVES = {
    "want to read": "want",
    "currently reading": "reading",
    "previously read": "read",
}
FORMATS = {"audiobook": "audiobook", "physical": "physical"}

NO_RESPONSE = "_no response_"
# Both capture greedily to the end of the line and are stripped by the caller.
# A lazy `.+?` followed by `\s*$` would mean the same thing but backtrack.
SECTION = re.compile(r"^### +(?P<label>.+)$", re.MULTILINE)
CHECKED = re.compile(r"^ *- \[[xX]\] +(?P<label>.+)$", re.MULTILINE)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def sections(body: str) -> dict[str, str]:
    """Split the rendered issue body into `{label: answer}`, blanks dropped."""
    found = {}
    matches = list(SECTION.finditer(body))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        answer = body[match.end():end].strip()
        if answer.lower() != NO_RESPONSE:
            found[match.group("label").strip().lower()] = answer
    return found


def slugify(title: str) -> str:
    """A URL-safe stem for the page, matching the shelf's existing slugs."""
    ascii_title = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug or "untitled"


def quote_list(values: list[str]) -> str:
    items = [v if re.fullmatch(r"[A-Za-z0-9-]+", v) else json.dumps(v) for v in values]
    return "[" + ", ".join(items) + "]"


def build(body: str) -> tuple[str, str]:
    """Read the issue body, return the page's slug and its markdown."""
    field = sections(body)

    title = field.get("title", "")
    author = field.get("author", "")
    if not title:
        fail("the issue has no Title — was it filed with the Add a book form?")
    if not author:
        fail("the issue has no Author — was it filed with the Add a book form?")

    shelf = SHELVES.get(field.get("shelf", "").lower())
    if not shelf:
        fail(f"unknown shelf {field.get('shelf', '')!r}")

    lines = ["---", f'title: "{escape(title)}"']
    if subtitle := field.get("subtitle"):
        lines.append(f'description: "{escape(subtitle)}"')
    lines.append(f'author: "{escape(author)}"')

    book_format = FORMATS.get(field.get("format", "").lower(), "")
    narrator = field.get("narrator", "")
    if narrator and book_format == "audiobook":
        lines.append(f'narrator: "{escape(narrator)}"')
    if book_format:
        lines.append(f"format: {book_format}")
    lines.append(f"shelf: {shelf}")

    years = re.findall(r"\d{4}", field.get("year(s) finished", ""))
    if shelf == "read":
        if not years:
            fail("a previously read book needs at least one year finished")
        lines.append("read_years: [" + ", ".join(sorted(years, reverse=True)) + "]")
    elif years:
        fail(f"year(s) finished is set but the shelf is {field.get('shelf')!r}")

    rating = field.get("rating", "")
    if rating.isdigit():
        lines.append(f"rating: {rating}")

    tags = sorted(label.strip() for label in CHECKED.findall(field.get("tags", "")))
    if tags:
        lines.append("tags: " + quote_list(tags))
    lines.append("---")

    notes = field.get("thoughts", "").strip()
    lines += ["", notes + "\n" if notes else "*No thoughts written yet.*\n"]
    return slugify(title), "\n".join(lines)


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: add_book.py <issue-body-file>")

    slug, page = build(Path(sys.argv[1]).read_text(encoding="utf-8"))
    path = (DOCS / f"{slug}.md").resolve()
    # `slugify` already reduces the title to `[a-z0-9-]`, so it cannot climb out
    # of `docs/`. Say so to the filesystem anyway: this writes a file from the
    # body of a public issue, and the check costs nothing.
    if path.parent != DOCS.resolve():
        fail(f"refusing to write outside docs/: {path}")
    if path.exists():
        fail(f"{path.relative_to(ROOT)} already exists — that book is on the shelf")

    path.write_text(page, encoding="utf-8")
    print(f"created: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
