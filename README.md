# Shelf — a markdown reading journal

A [Zensical](https://zensical.org) site: one markdown page per book, straight
in `docs/`, so every book gets its own URL at the root of the domain
(`/the-hobbit/`). Three tabs sit across the top — currently reading,
previously read, want to read. Each shelf page is a plain list of links, one
per book, with its format icon and a tooltip (author, narrator, rating).
Under **Previously read** the years are section headers in the sidebar, not
pages of their own — the single `previously-read/index.md` page groups
finished books under a heading per year.

```
docs/
  index.md               # Currently reading  →  /
  want-to-read.md        # Want to read       →  /want-to-read/
  previously-read/
    index.md             # Previously read    →  /previously-read/
  the-hobbit.md          # a book             →  /the-hobbit/
```

## Build

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

zensical serve     # preview on http://localhost:8000
zensical build     # -> site/
```

## Adding a book

Create `docs/my-book.md` with just frontmatter and your notes — no heading,
no metadata block. `scripts/shelves.py` generates all of that from the
frontmatter fields on every run, so writing it by hand would just be
overwritten:

```md
---
title: "The Book Title"
description: "An Optional Secondary Title"
author: "The Author"
narrator: "Some Narrator"      # omit for a book with no narrator
format: audiobook                # audiobook | physical
status: want                     # reading | read | want
tags: [nonfiction, favorites]    # optional, freeform
---

Your thoughts go here, in plain markdown. Anything Zensical supports —
admonitions, footnotes, tables, code blocks — works too.
```

Run `python3 scripts/shelves.py` (or push — the **Update shelves** workflow
does this for you) and it fills in everything above your notes: the heading
with the right icon, and an `Author` / `Format` / `Status` / `Rating` / `Tags`
definition list — each on its own line, not crammed into one — built entirely
from the frontmatter. That generated block is rewritten every run, so don't
hand-edit it; only the frontmatter and the notes below the `---` are yours.

That book page's frontmatter is the only place its state lives.

## Marking a book as read

Change two fields and push:

```diff
- status: reading
+ status: read
+ read_years: [2026]
+ rating: 5   # optional, 1-5
```

A book read more than once lists every year, newest first:
`read_years: [2026, 2024]`. The **Update shelves** workflow
(`.github/workflows/shelves.yml`) reruns `scripts/shelves.py`, which rereads
every book page's frontmatter and rewrites everything that lists it:

- the book's own page (heading icon, metadata block)
- `docs/index.md`, `docs/want-to-read.md` and `docs/previously-read/index.md`,
  including the counts in each intro line and the year headings themselves —
  a first book finished in a new year adds that heading
- `docs/tags/index.md`, grouping every tagged book under its tags
- the `nav` table in `zensical.toml`, so the sidebar (including each year's
  section header under Previously read, and the Tags tab) and the
  previous/next links follow

Because `status`, `read_years`, and the heading icon are all separate,
structured fields instead of words packed into one line, a half-finished edit
can't leave a book stuck on the wrong shelf the way a hand-typed status
sentence could.

It commits the result back to `main`, then the deploy workflow publishes. Run
it yourself with `python3 scripts/shelves.py`, or `--check` to see what is out
of date without writing (that is what runs on pull requests). `--check` also
validates every book's frontmatter — an unknown `status`, a `read` book with
no `read_years`, or a `rating` outside 1–5 fails the check with a clear error
instead of silently miscategorizing the book.

## Tags

Add a `tags:` list to any book's frontmatter — freeform, no fixed list to
maintain:

```yaml
tags: [nonfiction, business, favorites]
```

`scripts/shelves.py` collects every tag in use into `docs/tags/index.md`
(linked from the nav as **Tags**), one section per tag with every book that
carries it, and links each book's own `Tags` line back to that section.

## Icons

`docs/assets/favicon.svg` is the same Lucide `book-open-text` mark as the site
logo. `scripts/icons.py` rasterises it into the favicon, apple-touch and web
app manifest icons next to it; the outputs are checked in, so run it only when
the mark changes:

```sh
pip install cairosvg pillow
python3 scripts/icons.py
```
