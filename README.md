# Shelf — a markdown reading journal

A [Zensical](https://zensical.org) site: one markdown page per book, straight
in `docs/`, so every book gets its own URL at the root of the domain
(`/the-hobbit/`). Three tabs sit across the top — currently reading,
previously read, want to read — and each year I've finished books in is a page
under **Previously read**.

```
docs/
  index.md               # Currently reading  →  /
  want-to-read.md        # Want to read       →  /want-to-read/
  previously-read/
    index.md             # Previously read    →  /previously-read/
    2026.md              # a page per year    →  /previously-read/2026/
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

Create `docs/my-book.md`:

```md
---
title: The Book Title
description: An Optional Secondary Title
---

# :lucide-book: The Book Title

*An Optional Secondary Title*

:lucide-user: **The Author** · :lucide-headphones: Audiobook ·
:lucide-mic: Read by Some Narrator · :lucide-book: Read in 2026 ·
:lucide-star: :lucide-star: :lucide-star: :lucide-star: 4/5

---

Your thoughts go here, in plain markdown. Anything Zensical supports —
admonitions, footnotes, tables, code blocks — works too.
```

The title icon marks where the book sits: `:lucide-book:` for finished,
`:lucide-book-marked:` for in progress, `:lucide-book-plus:` for want to read.
Formats use `:lucide-headphones:` (audiobook) or `:lucide-book-open:`
(physical), and ratings are one `:lucide-star:` per star. A book read more than
once lists every year, newest first: `:lucide-book: Read in 2026, 2024`.

That book page is the only place its state lives.

## Marking a book as read

Change the marker on the book's own metadata line — `:lucide-book-marked:
Reading` becomes `:lucide-book: Read in 2026` — and push. The **Update
shelves** workflow (`.github/workflows/shelves.yml`) reruns
`scripts/shelves.py`, which rereads every book page and rewrites everything
that lists it:

- `docs/index.md`, `docs/want-to-read.md` and `docs/previously-read/*.md`,
  including the counts in each intro line and the year pages themselves — a
  first book finished in a new year creates that year's page
- the `nav` table in `zensical.toml`, so the sidebar and the previous/next
  links follow

It commits the result back to `main`, then the deploy workflow publishes. Run
it yourself with `python3 scripts/shelves.py`, or `--check` to see what is out
of date without writing (that is what runs on pull requests).

## Icons

`docs/assets/favicon.svg` is the same Lucide `book-open-text` mark as the site
logo. `scripts/icons.py` rasterises it into the favicon, apple-touch and web
app manifest icons next to it; the outputs are checked in, so run it only when
the mark changes:

```sh
pip install cairosvg pillow
python3 scripts/icons.py
```
