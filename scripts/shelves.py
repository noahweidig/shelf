#!/usr/bin/env python3
"""Rebuild every generated page from the book pages' own frontmatter.

Every book in `docs/` carries its state as frontmatter fields, not prose:

    ---
    title: "Atomic Habits"
    description: "An Easy & Proven Way to Build Good Habits & Break Bad Ones"
    author: "James Clear"
    narrator: "James Clear"
    format: audiobook
    status: read
    read_years: [2025]
    rating: 5
    tags: [nonfiction, habits]
    ---

This script reads all of them and rewrites everything that lists or displays
them: each book page's own heading/metadata block, the shelf pages
(`index.md` "Currently reading", `want-to-read.md`, `previously-read/index.md`),
the tags index (`docs/tags/index.md`), and the `nav` table in
`zensical.toml`. So marking a book as read is a frontmatter edit to that
book's own page: everything else follows from it.

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
TAGS = DOCS / "tags"
CONFIG = ROOT / "zensical.toml"

SHELF_PAGES = {"index.md", "want-to-read.md"}

READING = "reading"
READ = "read"
WANT = "want"
STATUSES = {READING, READ, WANT}

STATUS_ICON = {READING: ":lucide-book-marked:", READ: ":lucide-book:", WANT: ":lucide-book-plus:"}
STATUS_LABEL = {READING: "Reading", WANT: "Want to read"}

FORMAT_ICON = {"audiobook": ":lucide-headphones:", "physical": ":lucide-book-open:"}
FORMAT_LABEL = {"audiobook": "Audiobook", "physical": "Physical"}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
SEPARATOR = re.compile(r"\n---\n")
MARKDOWN_SPECIAL = re.compile(r"([*_\[\]`])")
FIELD = re.compile(r"^(\w+):\s*(.*?)\s*$")
TAG_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Book:
    slug: str
    title: str
    subtitle: str
    author: str
    narrator: str
    format: str  # "audiobook" | "physical" | ""
    status: str
    years: list[int]
    rating: int = 0
    tags: list[str] = field(default_factory=list)
    notes: str = "*No thoughts written yet.*\n"

    @property
    def sort_key(self) -> str:
        return self.title.lower()

    @property
    def format_icon(self) -> str:
        return FORMAT_ICON.get(self.format, "")

    @property
    def format_label(self) -> str:
        return FORMAT_LABEL.get(self.format, "")

    def status_text(self) -> str:
        if self.status == READ:
            return "Read in " + ", ".join(str(year) for year in self.years)
        return STATUS_LABEL[self.status]

    def tooltip(self) -> str:
        parts = [f"by {self.author}"]
        if self.narrator:
            parts[0] += f" · read by {self.narrator}"
        if self.format_label:
            parts.append(self.format_label)
        if self.rating:
            parts.append(f"{self.rating}/5")
        if self.status == READ:
            parts.append(self.status_text())
        return " · ".join(parts).replace('"', "'")

    def link(self, prefix: str = "") -> str:
        """Render the book as one line: icon, title link, tooltip."""
        icon = self.format_icon or STATUS_ICON[self.status]
        title = markdown_escape(self.title)
        return f'-   {icon} [{title}]({prefix}{self.slug}.md "{self.tooltip()}")'


def markdown_escape(value: str) -> str:
    """Keep punctuation literal inside heading/link text that markdown would parse."""
    return MARKDOWN_SPECIAL.sub(r"\\\1", value)


def tag_slug(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


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


def parse_list(value: str) -> list[str]:
    """Read a flow-style YAML list: `[a, "b c", d]`. Empty for `[]` or a bare scalar."""
    inner = value.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        return []
    inner = inner[1:-1].strip()
    if not inner:
        return []
    return [unquote(item.strip()) for item in inner.split(",")]


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def book_pages() -> list[Path]:
    """Every page in `docs/` that is a book — one URL per book, at the site root.

    A page counts as a book when its frontmatter has a `status` field.
    """
    pages = []
    for path in sorted(DOCS.glob("*.md")):
        if path.name in SHELF_PAGES:
            continue
        frontmatter = FRONTMATTER.match(path.read_text(encoding="utf-8"))
        if frontmatter and re.search(r"^status:", frontmatter.group(1), re.MULTILINE):
            pages.append(path)
    return pages


def parse_book(path: Path) -> Book:
    text = path.read_text(encoding="utf-8")

    frontmatter = FRONTMATTER.match(text)
    if not frontmatter:
        fail(f"{path.relative_to(ROOT)}: missing frontmatter")

    meta: dict[str, str | list[str]] = {}
    for line in frontmatter.group(1).splitlines():
        matched = FIELD.match(line)
        if not matched:
            continue
        key, raw_value = matched.group(1), matched.group(2)
        meta[key] = parse_list(raw_value) if raw_value.startswith("[") else unquote(raw_value)

    rel = path.relative_to(ROOT)
    if "title" not in meta:
        fail(f"{rel}: frontmatter has no title")

    status = meta.get("status", "")
    if status not in STATUSES:
        fail(f"{rel}: status must be one of {sorted(STATUSES)}, got {status!r}")

    author = meta.get("author", "")
    if not author:
        fail(f"{rel}: frontmatter has no author")

    book_format = meta.get("format", "")
    if book_format and book_format not in FORMAT_ICON:
        fail(f"{rel}: format must be one of {sorted(FORMAT_ICON)}, got {book_format!r}")

    years_raw = meta.get("read_years", [])
    years = sorted((int(y) for y in years_raw), reverse=True) if years_raw else []
    if status == READ and not years:
        fail(f"{rel}: status is read but read_years is empty")
    if status != READ and years:
        fail(f"{rel}: read_years is set but status is not read")

    rating_raw = meta.get("rating", "")
    rating = int(rating_raw) if rating_raw else 0
    if rating and not 1 <= rating <= 5:
        fail(f"{rel}: rating must be between 1 and 5, got {rating}")

    tags = meta.get("tags", []) if isinstance(meta.get("tags", []), list) else []
    for tag in tags:
        if not TAG_SLUG.match(tag):
            fail(f"{rel}: tag {tag!r} must be lowercase words separated by hyphens")

    body = text[frontmatter.end():]
    separator = SEPARATOR.search(body)
    notes = body[separator.end():].lstrip("\n") if separator else "*No thoughts written yet.*\n"

    return Book(
        slug=path.stem,
        title=meta["title"],
        subtitle=meta.get("description", ""),
        author=author,
        narrator=meta.get("narrator", ""),
        format=book_format,
        status=status,
        years=years,
        rating=rating,
        tags=sorted(tags),
        notes=notes,
    )


def render_book_page(book: Book) -> str:
    """Rebuild a book's own page: frontmatter, then a generated heading and
    metadata block, then the notes the reader actually wrote, untouched.
    """
    fm = ['---', f'title: "{escape(book.title)}"']
    if book.subtitle:
        fm.append(f'description: "{escape(book.subtitle)}"')
    fm.append(f'author: "{escape(book.author)}"')
    if book.narrator:
        fm.append(f'narrator: "{escape(book.narrator)}"')
    if book.format:
        fm.append(f'format: {book.format}')
    fm.append(f'status: {book.status}')
    if book.status == READ:
        fm.append('read_years: [' + ", ".join(str(y) for y in book.years) + ']')
    if book.rating:
        fm.append(f'rating: {book.rating}')
    if book.tags:
        fm.append('tags: [' + ", ".join(book.tags) + ']')
    fm.append('---')

    icon = STATUS_ICON[book.status]
    title = markdown_escape(book.title)
    lines = fm + ['', f'# {icon} {title}']
    if book.subtitle:
        lines += ['', f'*{markdown_escape(book.subtitle)}*']

    lines += ['', 'Author', f':   {markdown_escape(book.author)}']

    if book.format:
        format_line = f'{book.format_icon} {book.format_label}'
        if book.narrator:
            format_line += f' — read by {markdown_escape(book.narrator)}'
        lines += ['', 'Format', f':   {format_line}']

    lines += ['', 'Status', f':   {icon} {book.status_text()}']

    if book.rating:
        stars = " ".join([":lucide-star:"] * book.rating)
        lines += ['', 'Rating', f':   {stars} ({book.rating}/5)']

    if book.tags:
        chips = " · ".join(
            f'[{tag}](tags/index.md#{tag_slug(tag)})' for tag in book.tags
        )
        lines += ['', 'Tags', f':   {chips}']

    lines += ['', '---', '', book.notes.rstrip("\n") + "\n"]
    return "\n".join(lines)


def page(frontmatter_title: str, description: str, heading: str, intro: str,
         books: list[Book]) -> str:
    """Render a shelf page: frontmatter, heading, intro line, link list."""
    links = "\n".join(book.link() for book in books)
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
        f"{links}\n"
    )


def plural(count: int, singular: str, many: str) -> str:
    return f"{count} {singular if count == 1 else many}"


def render_pages(books: list[Book]) -> dict[Path, str]:
    reading = sorted((b for b in books if b.status == READING), key=lambda b: b.sort_key)
    finished = sorted((b for b in books if b.status == READ), key=lambda b: b.sort_key)
    waiting = sorted((b for b in books if b.status == WANT), key=lambda b: b.sort_key)
    years = sorted({year for book in finished for year in book.years}, reverse=True)

    listened = sum(1 for b in finished if b.format == "audiobook")
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
        TAGS / "index.md": tags_index(books),
    }
    for book in books:
        book_path = DOCS / f"{book.slug}.md"
        pages[book_path] = render_book_page(book)
    return pages


def breakdown(books: list[Book]) -> str:
    """How a year's books were read: `:lucide-headphones: 14 · :lucide-book-open: 6`."""
    counts = {
        ":lucide-headphones: %d listened to": "audiobook",
        ":lucide-book-open: %d in print": "physical",
    }
    parts = []
    for template, book_format in counts.items():
        count = sum(1 for book in books if book.format == book_format)
        if count:
            parts.append(template % count)
    return " · ".join(parts)


def previously_read_index(finished: list[Book], years: list[int]) -> str:
    """The Previously read page: every finished book, grouped under a year heading."""
    sections = []
    for year in years:
        of_year = sorted(
            (book for book in finished if year in book.years), key=lambda b: b.sort_key
        )
        lines = [f"## {year}", "", f"{plural(len(of_year), 'book', 'books')} "
                  f"finished · {breakdown(of_year)}", ""]
        lines += [book.link(prefix="../") for book in of_year]
        sections.append("\n".join(lines))
    if not years:
        span_phrase = ""
    elif len(years) > 1:
        span_phrase = f" between {years[-1]}–{years[0]}"
    else:
        span_phrase = f" in {years[0]}"
    return (
        "---\n"
        'title: "Previously read"\n'
        'description: "Every book I have finished."\n'
        "---\n"
        "\n"
        "# :lucide-book: Previously read\n"
        "\n"
        f"{plural(len(finished), 'book', 'books')} finished{span_phrase}.\n"
        "\n" + "\n\n".join(sections) + "\n"
    )


def tags_index(books: list[Book]) -> str:
    """The Tags page: every tag in use, grouped alphabetically, linking its books."""
    by_tag: dict[str, list[Book]] = {}
    for book in books:
        for tag in book.tags:
            by_tag.setdefault(tag, []).append(book)

    sections = []
    for tag in sorted(by_tag):
        of_tag = sorted(by_tag[tag], key=lambda b: b.sort_key)
        lines = [f'## {tag} {{: #{tag_slug(tag)} }}', "", f"{plural(len(of_tag), 'book', 'books')}", ""]
        lines += [book.link(prefix="../") for book in of_tag]
        sections.append("\n".join(lines))

    body = "\n\n".join(sections) if sections else "*No tags yet.*\n"
    return (
        "---\n"
        'title: "Tags"\n'
        'description: "Every book, grouped by tag."\n'
        "---\n"
        "\n"
        "# :lucide-tag: Tags\n"
        "\n"
        f"{plural(len(by_tag), 'tag', 'tags')} across the shelf.\n"
        "\n" + body + "\n"
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
        # so it appears exactly once in the sidebar. The year itself is a
        # section header only — no page of its own.
        of_year = [book for book in finished if book.years[0] == year]
        lines.append(f'    {{ "{year}" = [')
        lines += [
            f'      {{ "{escape(book.title)}" = "{book.slug}.md" }},'
            for book in of_year
        ]
        lines.append("    ] },")
    lines += ["  ] },", '  { "Want to read" = [', '    "want-to-read.md",']
    lines += entries(waiting)
    lines += ["  ] },", '  "tags/index.md",', "]"]
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
    for path in outputs:
        if path in changed:
            print(f"updated: {path.relative_to(ROOT)}")
    for path in stale:
        print(f"removed: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
