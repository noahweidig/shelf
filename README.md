# Shelf — a markdown reading journal

A [Zensical](https://zensical.org) site: one markdown page per book in
`docs/books/`, plus a page per shelf — currently reading, each year I've
finished books in, and want to read — each of them a tab in the top navigation.

## Build

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

zensical serve     # preview on http://localhost:8000
zensical build     # -> site/
```

Nothing is generated: every page under `docs/` is checked in and edited by hand.

## Adding a book

Create `docs/books/my-book.md`:

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
(physical), and ratings are one `:lucide-star:` per star.

Then add a card for it on the matching shelf page (`index.md`,
`want-to-read.md`, or `<year>.md`) and an entry under that page's section in
`nav` in `zensical.toml`, so it shows up in the sidebar and in the
previous/next links at the foot of each page.
