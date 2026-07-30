#!/usr/bin/env python3
"""Rebuild the shelf pages and the nav from the book pages themselves.

Every book in `docs/` carries its own state on its metadata line:

    :lucide-user: **Author** · :lucide-headphones: Audiobook ·
    :lucide-mic: Read by Narrator · :lucide-book: Read in 2026, 2024

This script reads all of them and rewrites the shelves that list them —
`index.md` (currently reading), `docs/previously-read/<year>.md`,
`want-to-read.md` — plus the `nav` table in `zensical.toml`. So marking a
book as read is a one-line edit to that book's page: everything else
follows from it.

Usage: python3 scripts/shelves.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PREVIOUSLY_READ = DOCS / "previously-read"
CONFIG = ROOT / "zensical.toml"

SHELF_PAGES = {"index.md", "want-to-read.md"}

READING = "reading"
READ = "read"
WANT = "want"

ICON = {READING: ":lucide-book-marked:", READ: ":lucide-book:", WANT: ":lucide-book-plus:"}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
META_LINE = re.compile(r"^:lucide-user: .*$", re.MULTILINE)
FIELD = re.compile(r"^(\w+):\s*(.*?)\s*$")


@dataclass
class Book:
    slug: str
    title: str
    subtitle: str
    author: str
    narrator: str
    format: str
    status: str
    years: list[int]
    rating: str = ""
    sources: list[str] = field(default_factory=list)

    @property
    def status_text(self) -> str:
        if self.status == READING:
            return "Reading"
        if self.status == WANT:
            return "Want to read"
        return "Read in " + ", ".join(str(year) for year in self.years)

    @property
    def sort_key(self) -> str:
        return self.title.lower()

    def card(self) -> str:
        """Render the book as a `grid cards` entry for a shelf page."""
        lines = [f"-   **[{self.title}]({self.slug}.md)**", "", "    ---", ""]
        if self.subtitle:
            lines += [f"    *{self.subtitle}*", ""]
        byline = f"by {self.author}"
        if self.narrator:
            byline += f" · read by {self.narrator}"
        state = f"{ICON[self.status]} {self.status_text}"
        if self.format:
            state += f" · {self.format}"
        if self.rating:
            state += f" · {self.rating}"
        lines += [f"    {byline}", "", f"    {state}"]
        return "\n".join(lines)


def unquote(value: str) -> str:
    """Read a YAML scalar: double-quoted values may carry escapes like \\u00e9."""
    if len(value) > 1 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) > 1 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def book_pages() -> list[Path]:
    """Every page in `docs/` that is a book — one URL per book, at the site root.

    The shelves themselves live alongside them, so a page counts as a book when
    it carries a `:lucide-user:` metadata line.
    """
    return [
        path
        for path in sorted(DOCS.glob("*.md"))
        if path.name not in SHELF_PAGES
        and META_LINE.search(path.read_text(encoding="utf-8"))
    ]


def parse_book(path: Path) -> Book:
    text = path.read_text(encoding="utf-8")

    frontmatter = FRONTMATTER.match(text)
    if not frontmatter:
        fail(f"{path.relative_to(ROOT)}: missing frontmatter")
    meta: dict[str, str] = {}
    for line in frontmatter.group(1).splitlines():
        matched = FIELD.match(line)
        if matched:
            meta[matched.group(1)] = unquote(matched.group(2))
    if "title" not in meta:
        fail(f"{path.relative_to(ROOT)}: frontmatter has no title")

    meta_line = META_LINE.search(text)
    if not meta_line:
        fail(f"{path.relative_to(ROOT)}: no `:lucide-user:` metadata line")

    author = narrator = book_format = rating = ""
    status = ""
    years: list[int] = []
    for part in (p.strip() for p in meta_line.group(0).split(" · ")):
        if part.startswith(":lucide-user:"):
            author = part.removeprefix(":lucide-user:").strip().strip("*")
        elif part.startswith(":lucide-mic:"):
            narrator = part.removeprefix(":lucide-mic: Read by").strip()
        elif part.startswith((":lucide-headphones:", ":lucide-book-open:")):
            book_format = part
        elif part.startswith(":lucide-star:"):
            rating = part
        elif part.startswith(":lucide-book-marked:"):
            status = READING
        elif part.startswith(":lucide-book-plus:"):
            status = WANT
        elif part.startswith(":lucide-book:"):
            status = READ
            years = sorted(
                (int(y) for y in re.findall(r"\b(\d{4})\b", part)), reverse=True
            )

    if not status:
        fail(f"{path.relative_to(ROOT)}: metadata line has no shelf marker")
    if status == READ and not years:
        fail(f"{path.relative_to(ROOT)}: marked read but names no year")
    if not author:
        fail(f"{path.relative_to(ROOT)}: metadata line has no author")

    return Book(
        slug=path.stem,
        title=meta["title"],
        subtitle=meta.get("description", ""),
        author=author,
        narrator=narrator,
        format=book_format,
        status=status,
        years=years,
        rating=rating,
    )


def page(frontmatter_title: str, description: str, heading: str, intro: str,
         books: list[Book], depth: int = 0) -> str:
    """Render a shelf page: frontmatter, heading, intro line, card grid."""
    prefix = "../" * depth
    cards = "\n\n".join(
        book.card().replace(f"]({book.slug}.md)", f"]({prefix}{book.slug}.md)")
        for book in books
    )
    return (
        "---\n"
        f'title: "{frontmatter_title}"\n'
        f'description: "{description}"\n'
        "---\n"
        "\n"
        f"# {heading}\n"
        "\n"
        f"{intro}\n"
        "\n"
        '<div class="grid cards" markdown>\n'
        "\n"
        f"{cards}\n"
        "\n"
        "</div>\n"
    )


def plural(count: int, singular: str, many: str) -> str:
    return f"{count} {singular if count == 1 else many}"


def render_pages(books: list[Book]) -> dict[Path, str]:
    reading = sorted((b for b in books if b.status == READING), key=lambda b: b.sort_key)
    finished = sorted((b for b in books if b.status == READ), key=lambda b: b.sort_key)
    waiting = sorted((b for b in books if b.status == WANT), key=lambda b: b.sort_key)
    years = sorted({year for book in finished for year in book.years}, reverse=True)

    listened = sum(1 for b in finished if b.format.startswith(":lucide-headphones:"))
    pages = {
        DOCS / "index.md": page(
            "Currently reading",
            "Books I'm reading right now.",
            ":lucide-book-marked: Currently reading",
            f"The {len(reading)} books I have open right now. {len(finished)} finished, "
            f"{len(waiting)} waiting, {listened} of them listened to rather than read.",
            reading,
        ),
        DOCS / "want-to-read.md": page(
            "Want to read",
            "Books waiting on the shelf.",
            ":lucide-book-plus: Want to read",
            f"{plural(len(waiting), 'book', 'books')} waiting "
            f"{'its' if len(waiting) == 1 else 'their'} turn.",
            waiting,
        ),
        PREVIOUSLY_READ / "index.md": previously_read_index(finished, years),
    }
    for year in years:
        of_year = [book for book in finished if year in book.years]
        pages[PREVIOUSLY_READ / f"{year}.md"] = page(
            f"Read in {year}",
            f"Books finished in {year}.",
            f":lucide-book: Read in {year}",
            f"{plural(len(of_year), 'book', 'books')} finished in {year}.",
            of_year,
            depth=1,
        )
    return pages


def breakdown(books: list[Book]) -> str:
    """How a year's books were read: `:lucide-headphones: 14 · :lucide-book-open: 6`."""
    counts = {
        ":lucide-headphones: %d listened to": ":lucide-headphones:",
        ":lucide-book-open: %d in print": ":lucide-book-open:",
    }
    parts = []
    for template, icon in counts.items():
        count = sum(1 for book in books if book.format.startswith(icon))
        if count:
            parts.append(template % count)
    return " · ".join(parts)


def previously_read_index(finished: list[Book], years: list[int]) -> str:
    """The landing page for the Previously read tab: one card per year."""
    cards = []
    for year in years:
        of_year = [book for book in finished if year in book.years]
        cards.append(
            "\n".join(
                [
                    f"-   **[Read in {year}]({year}.md)**",
                    "",
                    "    ---",
                    "",
                    f"    {plural(len(of_year), 'book', 'books')} finished in {year}.",
                    "",
                    f"    {breakdown(of_year)}",
                ]
            )
        )
    span = f"{years[-1]}–{years[0]}" if len(years) > 1 else str(years[0])
    return (
        "---\n"
        'title: "Previously read"\n'
        'description: "Every book I have finished, a page per year."\n'
        "---\n"
        "\n"
        "# :lucide-book: Previously read\n"
        "\n"
        f"{plural(len(finished), 'book', 'books')} finished between {span}, a page per year.\n"
        "\n"
        '<div class="grid cards" markdown>\n'
        "\n" + "\n\n".join(cards) + "\n"
        "\n"
        "</div>\n"
    )


def render_nav(books: list[Book]) -> str:
    reading = sorted((b for b in books if b.status == READING), key=lambda b: b.sort_key)
    finished = sorted((b for b in books if b.status == READ), key=lambda b: b.sort_key)
    waiting = sorted((b for b in books if b.status == WANT), key=lambda b: b.sort_key)
    years = sorted({year for book in finished for year in book.years}, reverse=True)

    def entries(shelf: list[Book], prefix: str = "") -> list[str]:
        return [
            f'    {{ "{escape(book.title)}" = "{prefix}{book.slug}.md" }},'
            for book in shelf
        ]

    lines = ["nav = [", '  { "Currently reading" = [', '    "index.md",']
    lines += entries(reading)
    lines += ["  ] },", '  { "Previously read" = [', '    "previously-read/index.md",']
    for year in years:
        # A re-read book is listed under the most recent year it was finished,
        # so it appears exactly once in the sidebar.
        of_year = [book for book in finished if book.years[0] == year]
        lines.append(f'    {{ "{year}" = [')
        lines.append(f'      "previously-read/{year}.md",')
        lines += [
            f'      {{ "{escape(book.title)}" = "{book.slug}.md" }},'
            for book in of_year
        ]
        lines.append("    ] },")
    lines += ["  ] },", '  { "Want to read" = [', '    "want-to-read.md",']
    lines += entries(waiting)
    lines += ["  ] },", "]"]
    return "\n".join(lines) + "\n"


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def update_config(nav: str) -> str:
    text = CONFIG.read_text(encoding="utf-8")
    start = text.index("nav = [")
    end = text.index("\n]\n", start) + len("\n]\n")
    return text[:start] + nav + text[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if anything is out of date, without writing",
    )
    args = parser.parse_args()

    books = [parse_book(path) for path in book_pages()]
    if not books:
        fail("no books found in docs/")

    outputs = render_pages(books)
    outputs[CONFIG] = update_config(render_nav(books))

    stale = []
    for path in sorted(PREVIOUSLY_READ.glob("*.md")) if PREVIOUSLY_READ.exists() else []:
        if path not in outputs:
            stale.append(path)

    changed = [
        path
        for path, content in outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ] + stale

    if args.check:
        for path in changed:
            print(f"out of date: {path.relative_to(ROOT)}")
        return 1 if changed else 0

    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for path in stale:
        path.unlink()
    for path in changed:
        print(f"updated: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
