# Shelf — a markdown reading journal

A [Zensical](https://zensical.org) site: one markdown page per book, straight
in `docs/`, so every book gets its own URL at the root of the domain
(`/the-hobbit/`). Three tabs sit across the top — currently reading,
previously read, want to read. Each shelf page is a grid of cards, one per
book, built from the theme's own `.grid.cards` styling. Under **Previously
read** the years are section headers in the sidebar, not pages of their own —
the single `previously-read/index.md` page groups finished books under a
heading per year.

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

The easiest way is the [**Add a book** issue
form](../../issues/new?template=add-book.yml): fill in the boxes, and the
`Add a book` workflow writes the page, reruns `scripts/shelves.py` and opens a
draft pull request for you. Nothing is published until you merge it.

By hand, create `docs/my-book.md` with just frontmatter and your notes — no
heading, no metadata block. `scripts/shelves.py` generates all of that from the
frontmatter fields on every run, so writing it yourself would just be
overwritten:

```md
---
title: "The Book Title"
description: "An Optional Secondary Title"
author: "The Author"
narrator: "Some Narrator"        # omit for a book with no narrator
format: audiobook                # audiobook | physical
shelf: want                      # reading | read | want
tags: ["Fantasy", "Classics"]    # optional, from the vocabulary below
---

Your thoughts go here, in plain markdown. Anything Zensical supports —
admonitions, footnotes, tables, code blocks — works too.
```

Run `python3 scripts/shelves.py` (or push — the **Update shelves** workflow
does this for you) and it fills in everything above your notes: the heading
with the right icon, and a metadata card of icons — author, format and
narrator, shelf, rating — built entirely from the frontmatter. Each icon
carries its field name as a tooltip, so nothing is lost by not spelling
`Author:` out. That generated block is rewritten every run, so don't
hand-edit it; only the frontmatter and the notes below the marker are yours.

That book page's frontmatter is the only place its state lives.

> The shelf field is called `shelf`, not `status`, on purpose: Zensical reads
> `status` from a page's frontmatter as its *nav status marker* and stamps an
> icon beside the page in the sidebar. `icon`, which Zensical also reads, is
> generated here deliberately — it is what puts each book's format icon in the
> sidebar.

## Marking a book as read

Change two fields and push:

```diff
- shelf: reading
+ shelf: read
+ read_years: [2026]
+ rating: 5   # optional, 1-5
```

A book read more than once lists every year, newest first:
`read_years: [2026, 2024]`. The **Update shelves** workflow
(`.github/workflows/shelves.yml`) reruns `scripts/shelves.py`, which rereads
every book page's frontmatter and rewrites everything that lists it:

- the book's own page (heading icon, metadata card)
- `docs/index.md`, `docs/want-to-read.md` and `docs/previously-read/index.md`,
  including the counts in each intro line and the year headings themselves —
  a first book finished in a new year adds that heading
- the `nav` table in `zensical.toml`, so the sidebar (including each year's
  section header under Previously read) and the previous/next links follow
- the tag checkboxes in `.github/ISSUE_TEMPLATE/add-book.yml`

Because `shelf`, `read_years`, and the heading icon are all separate,
structured fields instead of words packed into one line, a half-finished edit
can't leave a book stuck on the wrong shelf the way a hand-typed status
sentence could.

It commits the result back to `main`, then the deploy workflow publishes. Run
it yourself with `python3 scripts/shelves.py`, or `--check` to see what is out
of date without writing (that is what runs on pull requests). `--check` also
validates every book's frontmatter — an unknown `shelf`, a `read` book with
no `read_years`, a `rating` outside 1–5, or a tag outside the vocabulary fails
the check with a clear error instead of silently miscategorizing the book.

## Tags

Tags are Zensical's own: put a `tags:` list in a book's frontmatter and the
theme renders them as chips at the foot of the page, each with its own icon,
and feeds them to search. There is no tags page to generate — Zensical does
not build tag listings yet, so `overrides/partials/tags.html` points each chip
at the site's own search until it does. Delete that file when Zensical ships
listings and the upstream behaviour takes over.

The vocabulary is fixed, and `[project.extra.tags]` in `zensical.toml` is the
one place it is defined:

```toml
[project.extra.tags]
Fantasy = "fantasy"          # tag name -> icon identifier

[project.theme.icon.tag]
fantasy = "lucide/wand-sparkles"
```

Adding a tag means adding it in both tables and nowhere else:
`scripts/shelves.py` reads them to validate every book's tags and to
regenerate the checkbox list in the issue form, and Zensical reads them to
pick each chip's icon. A tag that is not there fails `--check`.

## Icons

`docs/assets/favicon.svg` is the same Lucide `book-open-text` mark as the site
logo. `scripts/icons.py` rasterises it into the favicon, apple-touch and web
app manifest icons next to it; the outputs are checked in, so run it only when
the mark changes:

```sh
pip install cairosvg pillow
python3 scripts/icons.py
```

`docs/stylesheets/extra.css` is the only hand-written CSS on the site — one
rule, so a tag chip pointed at search does not pick up the underline every
other link gets. Everything else is the theme's.
