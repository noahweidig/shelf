# Shelf — a markdown reading journal

One markdown file per book in `books/`, built into a [Zensical](https://zensical.org)
site: a landing page of cards plus one page per book, with the theme's built-in
search, dark mode, and navigation.

## Build

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

node build.js      # books/*.md -> docs/
zensical serve     # preview on http://localhost:8000
zensical build     # -> site/
```

`build.js` turns each book into `docs/books/<slug>.md` (front matter rendered as
a metadata line) and writes the shelf itself to `docs/index.md`. Those two are
generated, so they're gitignored — run `node build.js` before serving or
building. Everything else in `docs/` (the favicon and `stylesheets/extra.css`)
is checked in and left alone.

The site's name comes from `site_name` in `zensical.toml`. `build.js` keeps it
in sync with the GitHub owner's real name, so a fork shows the forker's name
without any manual edits.

## Adding a book

Create `books/my-book.md`:

```md
---
title: The Book Title
subtitle: An Optional Secondary Title
author: The Author
status: reading        # reading | read | want-to-read
stars: 4               # optional, 1-5, shown on finished books
format: audiobook      # audiobook | physical
narrator: Some Narrator   # optional, for audiobooks
date: 2026             # year read; comma-separated for re-reads
---

Your thoughts go here, in plain markdown. Zensical renders it, so anything
Material for MkDocs supports — admonitions, footnotes, tables, code blocks —
works too.
```

The landing page groups cards into **Currently reading**, **Read in \<year\>**,
and **Want to read**; each card links to the book's page, which shows author,
format, narrator, status, rating, and your thoughts.
