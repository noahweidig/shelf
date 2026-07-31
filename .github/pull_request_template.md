<!--
Adding or updating a book? The "Add a book" issue form does all of this for
you and opens the pull request itself:
https://github.com/noahweidig/shelf/issues/new?template=add-book.yml
-->

## What changed

<!-- One line. Which book, and what happened to it. -->

## Checklist

- [ ] Only the book's **frontmatter** and the notes below the generated block were hand-edited
- [ ] `shelf:` is one of `reading`, `read`, `want` — and `read_years:` is set if and only if it is `read`
- [ ] Every tag is in `[project.extra.tags]` in `zensical.toml`
- [ ] `python3 scripts/shelves.py` was run and its output committed (or CI will say so)
