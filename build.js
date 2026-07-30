#!/usr/bin/env node
// Turns books/*.md into the docs/ tree that Zensical builds:
//   books/<slug>.md  ->  docs/books/<slug>.md   (front matter rendered as a meta line)
//   books/*.md       ->  docs/index.md          (the shelf: grid cards, grouped)
// Run `node build.js` before `zensical build` / `zensical serve`.
const fs = require('fs'), path = require('path');
const { execSync } = require('child_process');
const https = require('https');

const SRC = path.join(__dirname, 'books');
const DOCS = path.join(__dirname, 'docs');
const CONFIG = path.join(__dirname, 'zensical.toml');

// Derive "<Name>'s Shelf" from the repo's GitHub owner, so a fork shows the
// forker's name without any manual edits. Falls back gracefully if the git
// remote isn't a GitHub URL or the API call fails (e.g. no network access).
function getGithubLogin() {
  // In GitHub Actions the owner is provided directly; no git parsing needed.
  if (process.env.GITHUB_REPOSITORY_OWNER) return process.env.GITHUB_REPOSITORY_OWNER;
  try {
    const url = execSync('git config --get remote.origin.url', { cwd: __dirname }).toString().trim();
    const m = url.match(/github\.com[:/]([^/]+)\/[^/]+?(?:\.git)?$/);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}
function fetchGithubName(login) {
  return new Promise(resolve => {
    const req = https.get({
      hostname: 'api.github.com',
      path: `/users/${encodeURIComponent(login)}`,
      headers: {
        'User-Agent': 'reading-list-build-script',
        // Unauthenticated requests are rate-limited on shared CI runners
        // (which made the build fall back to the capitalized login), so
        // authenticate with the workflow token when one is available.
        ...(process.env.GITHUB_TOKEN
          ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` }
          : {}),
      },
      timeout: 5000,
    }, res => {
      if (res.statusCode !== 200) { res.resume(); resolve(null); return; }
      let data = '';
      res.on('data', c => (data += c));
      res.on('end', () => {
        try {
          const name = JSON.parse(data).name;
          resolve(typeof name === 'string' && name.trim() ? name.trim() : null);
        } catch {
          resolve(null);
        }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}
// Returns null when the owner can't be determined (no GitHub remote, no
// network), so an offline build leaves the configured site_name alone.
async function resolveShelfName() {
  const login = getGithubLogin();
  const fullName = login ? await fetchGithubName(login) : null;
  const firstName = fullName
    ? fullName.split(/\s+/)[0]
    : login
      ? login[0].toUpperCase() + login.slice(1)
      : null;
  return firstName ? `${firstName}'s Shelf` : null;
}
let SHELF_NAME = 'My Shelf';

function readSiteName() {
  if (!fs.existsSync(CONFIG)) return null;
  const m = fs.readFileSync(CONFIG, 'utf8').match(/^site_name\s*=\s*"(.*)"\s*$/m);
  return m ? m[1] : null;
}

// Keep zensical.toml's site_name (header + browser title) in sync with the
// resolved name. Only the one value is touched, so hand edits elsewhere stick.
function syncSiteName(name) {
  if (!fs.existsSync(CONFIG)) return;
  const toml = fs.readFileSync(CONFIG, 'utf8');
  const next = toml.replace(/^site_name\s*=.*$/m, `site_name = ${JSON.stringify(name)}`);
  if (next !== toml) {
    fs.writeFileSync(CONFIG, next);
    console.log(`Updated site_name in zensical.toml -> ${name}`);
  }
}

// --- front matter ---
function parse(raw) {
  raw = raw.replace(/\r\n?/g, '\n'); // tolerate CRLF files
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  const meta = {};
  if (m) for (const line of m[1].split('\n')) {
    const i = line.indexOf(':');
    if (i > 0) {
      let v = line.slice(i + 1).trim();
      // strip optional surrounding quotes ("Title: Sub" style values)
      if (v.length > 1 && ((v[0] === '"' && v.endsWith('"')) || (v[0] === "'" && v.endsWith("'")))) v = v.slice(1, -1);
      meta[line.slice(0, i).trim().toLowerCase()] = v;
    }
  }
  return { meta, body: m ? m[2] : raw };
}

// --- markdown helpers ---
// Escape the characters that would otherwise be read as markdown when a
// title or author is dropped into generated prose.
const esc = s => String(s ?? '').replace(/([\\`*_[\]()#<>|])/g, '\\$1');
const yaml = s => JSON.stringify(String(s ?? '')); // valid YAML for front matter

const icon = {
  reading: ':lucide-book-open:',
  read: ':lucide-check:',
  want: ':lucide-bookmark:',
  audiobook: ':lucide-headphones:',
  physical: ':lucide-book:',
  author: ':lucide-user:',
  narrator: ':lucide-mic:',
};

// Star rating (stars: 1-5 in front matter) — shown only on finished books.
// Non-numeric or out-of-range values render nothing rather than breaking.
const stars = b => {
  const n = Math.max(0, Math.min(5, Math.round(+b.meta.stars) || 0));
  if (b.status !== 'read' || n < 1) return '';
  return `<span class="stars" title="${n} out of 5 stars">${'★'.repeat(n)}${'☆'.repeat(5 - n)}</span>`;
};

const formatLabel = m => (m.format === 'audiobook' ? 'Audiobook' : 'Physical');
const formatIcon = m => (m.format === 'audiobook' ? icon.audiobook : icon.physical);
const statusLabel = b => b.status === 'reading' ? 'Reading'
  : b.status === 'want-to-read' ? 'Want to read'
    : b.meta.date ? `Read in ${b.meta.date}` : 'Read';
const statusIcon = b => b.status === 'reading' ? icon.reading
  : b.status === 'want-to-read' ? icon.want : icon.read;

// --- page generation ---
function card(b) {
  const m = b.meta;
  const lines = [`-   **[${esc(m.title)}](books/${encodeURIComponent(b.slug)}.md)**`, '', '    ---', ''];
  if (m.subtitle) lines.push(`    *${esc(m.subtitle)}*`, '');
  // Plain text rather than icons here: 200+ cards of inline SVG adds up.
  const by = [m.author && `by ${esc(m.author)}`, m.narrator && `read by ${esc(m.narrator)}`]
    .filter(Boolean).join(' · ');
  if (by) lines.push(`    ${by}`, '');
  lines.push(`    ${[`${statusIcon(b)} ${statusLabel(b)}`, `${formatIcon(m)} ${formatLabel(m)}`, stars(b)]
    .filter(Boolean).join(' · ')}`);
  return lines.join('\n');
}

const section = (heading, list) => list.length
  ? `## ${heading}\n\n<div class="grid cards" markdown>\n\n${list.map(card).join('\n\n')}\n\n</div>\n`
  : '';

function bookPage(b) {
  const m = b.meta;
  const meta = [
    m.author && `${icon.author} **${esc(m.author)}**`,
    `${formatIcon(m)} ${formatLabel(m)}`,
    m.narrator && `${icon.narrator} Read by ${esc(m.narrator)}`,
    `${statusIcon(b)} ${statusLabel(b)}`,
    stars(b),
  ].filter(Boolean).join(' · ');
  const body = b.body.trim() || '*No thoughts written yet.*';
  return `---
title: ${yaml(m.title)}
${m.subtitle ? `description: ${yaml(m.subtitle)}\n` : ''}---

# ${esc(m.title)}
${m.subtitle ? `\n*${esc(m.subtitle)}*\n` : ''}
${meta}
{.shelf-meta}

---

${body}

[:lucide-arrow-left: All books](../index.md)
`;
}

// --- build ---
const STATUSES = new Set(['read', 'reading', 'want-to-read']);

async function main() {
  const resolved = await resolveShelfName();
  if (resolved) syncSiteName(resolved);
  SHELF_NAME = resolved || readSiteName() || SHELF_NAME;

  if (!fs.existsSync(SRC)) {
    console.error(`Error: source directory not found: ${SRC}`);
    process.exit(1);
  }

  const books = [];
  for (const f of fs.readdirSync(SRC).filter(f => f.endsWith('.md')).sort()) {
    try {
      const { meta, body } = parse(fs.readFileSync(path.join(SRC, f), 'utf8'));
      const slug = f.replace(/\.md$/, '');
      if (!meta.title) {
        // Fall back to a title derived from the filename instead of dying.
        meta.title = slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        console.warn(`Warning: ${f} has no title; using "${meta.title}"`);
      }
      let status = (meta.status || 'read').toLowerCase();
      if (!STATUSES.has(status)) {
        console.warn(`Warning: ${f} has unknown status "${status}"; treating as "read"`);
        status = 'read';
      }
      books.push({ slug, meta, body, status });
    } catch (e) {
      console.warn(`Warning: skipping ${f}: ${e.message}`);
    }
  }
  books.sort((a, b) => a.meta.title.localeCompare(b.meta.title));

  // Only the generated parts of docs/ are cleared; stylesheets/ and assets/
  // are checked in and left alone.
  fs.rmSync(path.join(DOCS, 'books'), { recursive: true, force: true });
  fs.mkdirSync(path.join(DOCS, 'books'), { recursive: true });

  const reading = books.filter(b => b.status === 'reading');
  const want = books.filter(b => b.status === 'want-to-read');
  const read = books.filter(b => b.status !== 'reading' && b.status !== 'want-to-read');

  // Group finished books by year read (date: 2026 — or comma-separated for re-reads: 2026, 2023).
  const byYear = new Map();
  for (const b of read) {
    const years = (b.meta.date || '').split(',').map(s => s.trim()).filter(Boolean);
    for (const y of years.length ? years : ['Earlier']) {
      if (!byYear.has(y)) byYear.set(y, []);
      byYear.get(y).push(b);
    }
  }
  const yearSections = [...byYear.keys()]
    .sort((a, b) => a === 'Earlier' ? 1 : b === 'Earlier' ? -1 : Number(b) - Number(a))
    .map(y => section(y === 'Earlier' ? 'Read' : `Read in ${y}`, byYear.get(y)))
    .join('\n');

  const audiobooks = books.filter(b => b.status !== 'want-to-read' && b.meta.format === 'audiobook').length;
  const index = `---
title: ${yaml(SHELF_NAME)}
description: Books I'm reading, books I've finished, and what I thought of them.
hide:
  - navigation
---

# ${esc(SHELF_NAME)}

Books I'm reading, books I've finished, and what I thought of them.

${icon.want} **${reading.length}** in progress ·
${icon.read} **${read.length}** finished ·
${icon.audiobook} **${audiobooks}** audiobooks ·
${icon.physical} **${want.length}** want to read
{.shelf-meta}

${section('Currently reading', reading)}
${yearSections}
${section('Want to read', want)}`;

  fs.writeFileSync(path.join(DOCS, 'index.md'), index.replace(/\n{3,}/g, '\n\n'));
  for (const b of books) fs.writeFileSync(path.join(DOCS, 'books', `${b.slug}.md`), bookPage(b));
  console.log(`Wrote ${books.length} books -> docs/`);
}

main().catch(e => { console.error(e); process.exit(1); });
