#!/usr/bin/env python3
"""
Build the /solutions/ section of rudraanshpatel.in.

Reads:   _solutions/*.md   any filename; files/folders starting with "_" are skipped
Writes:  solutions/index.html                        all entries, newest first
         solutions/<date>-<platform>-<id>/index.html one page per solution
         solutions/platform/<platform>/index.html    filtered lists
         solutions/tag/<tag>/index.html

Everything in solutions/ is generated. Edit the markdown, never the HTML.
Run locally:  pip install markdown pyyaml && python _tools/build_solutions.py
"""

import datetime as dt
import html
import re
import shutil
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_solutions"
OUT = ROOT / "solutions"
SITE = "https://rudraanshpatel.in"

FILENAME_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

# Short labels shown in lists. Anything not here is shown as written.
PLATFORM_SHORT = {
    "leetcode": "LC",
    "codeforces": "CF",
    "codechef": "CC",
    "geeksforgeeks": "GFG",
    "gfg": "GFG",
    "takeuforward": "TUF",
    "tuf": "TUF",
    "hackerrank": "HR",
    "atcoder": "AC",
    "cses": "CSES",
    "interviewbit": "IB",
    "spoj": "SPOJ",
}

# Difficulty -> existing .tag colour class in style.css
DIFFICULTY_CLASS = {
    "easy": "tag-live",
    "medium": "tag-planned",
    "hard": "tag-hard",
}

REQUIRED = ("platform", "title")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def esc(text):
    return html.escape(str(text), quote=True)


# ─────────────────────────── parsing ───────────────────────────

def parse_file(path):
    """Return an entry dict, or raise ValueError with a readable message."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path.name}: must start with a --- front matter block")
    try:
        _, fm_text, body = raw.split("---\n", 2)
    except ValueError:
        raise ValueError(f"{path.name}: front matter is missing its closing ---")

    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        hint = ""
        if "{{" in fm_text:
            hint = " (a {{...}} template placeholder wasn't filled in: use Insert template, not copy-paste)"
        raise ValueError(f"{path.name}: front matter is not valid YAML{hint}\n{e}")
    if not isinstance(fm, dict):
        raise ValueError(f"{path.name}: front matter must be key: value pairs")

    # Date: front matter `date:` wins; otherwise a YYYY-MM-DD at the start of the filename.
    raw_date = fm.get("date")
    if not raw_date:
        m = FILENAME_DATE_RE.match(path.name)
        raw_date = m.group(1) if m else None
    if not raw_date:
        raise ValueError(f"{path.name}: add a date, e.g.  date: 2026-10-21")
    if isinstance(raw_date, dt.datetime):
        date = raw_date.date()
    elif isinstance(raw_date, dt.date):
        date = raw_date
    else:
        try:
            date = dt.date.fromisoformat(str(raw_date).strip())
        except ValueError:
            raise ValueError(f"{path.name}: date '{raw_date}' should look like 2026-10-21")

    missing = [k for k in REQUIRED if not fm.get(k)]
    if missing:
        raise ValueError(f"{path.name}: missing required field(s): {', '.join(missing)}")

    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    tags = [slugify(t) for t in tags if str(t).strip()]

    difficulty = str(fm.get("difficulty") or "").strip()
    platform = str(fm["platform"]).strip()
    short = PLATFORM_SHORT.get(slugify(platform).replace("-", ""), platform)
    ident = str(fm.get("id") or "").strip()
    url_slug = f"{date.isoformat()}-{slugify(short)}-{slugify(ident or fm['title'])}"

    return {
        "file": path.name,
        "stem": url_slug,
        "date": date,
        "platform": platform,
        "platform_slug": slugify(platform),
        "platform_short": short,
        "id": ident,
        "title": str(fm["title"]).strip(),
        "link": str(fm.get("link") or "").strip(),
        "difficulty": difficulty,
        "tags": tags,
        "time": str(fm.get("time") or "").strip(),
        "space": str(fm.get("space") or "").strip(),
        "body_md": body.strip(),
    }


def render_md(text):
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )


# ─────────────────────────── shared bits ───────────────────────────

def head(title, description, path, og_type="website", noindex=False):
    robots = '\n  <meta name="robots" content="noindex" />' if noindex else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{esc(description)}" />{robots}

  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{SITE}{path}" />
  <meta property="og:type" content="{og_type}" />

  <title>{esc(title)}</title>
  <link rel="canonical" href="{SITE}{path}" />
  <link rel="stylesheet" href="/style.css" />
  <link rel="icon" type="image/x-icon" href="/avatar.ico">
</head>
"""


GENERATED_NOTE = "<!-- Generated by _tools/build_solutions.py. Edit _solutions/*.md instead. -->\n"


def difficulty_tag(e):
    if not e["difficulty"]:
        return ""
    cls = DIFFICULTY_CLASS.get(e["difficulty"].lower(), "tag-archived")
    return f' <span class="tag {cls}">{esc(e["difficulty"])}</span>'


def complexity_text(e):
    parts = []
    if e["time"]:
        parts.append(f"T {e['time']}")
    if e["space"]:
        parts.append(f"S {e['space']}")
    return " · ".join(parts)


def display_title(e):
    return f"{e['id']}. {e['title']}" if e["id"] else e["title"]


# ─────────────────────────── list pages ───────────────────────────

def filter_bar(entries, active=None):
    platforms = Counter((e["platform_slug"], e["platform"]) for e in entries)
    tags = Counter(t for e in entries for t in e["tags"])

    def link(href, label, key):
        if key == active:
            return f"<strong>{esc(label)}</strong>"
        return f'<a href="{href}">{esc(label)}</a>'

    plat_links = [link("/solutions/", f"all ({len(entries)})", None)]
    for (slug, name), n in sorted(platforms.items(), key=lambda x: (-x[1], x[0][1])):
        plat_links.append(link(f"/solutions/platform/{slug}/", f"{name} ({n})", f"p:{slug}"))

    tag_links = [
        link(f"/solutions/tag/{t}/", f"{t} ({n})", f"t:{t}")
        for t, n in sorted(tags.items(), key=lambda x: (-x[1], x[0]))
    ]

    out = f'  <p class="mono dim sol-filter">platform: {" · ".join(plat_links)}</p>\n'
    if tag_links:
        out += f'  <p class="mono dim sol-filter">tags: {" · ".join(tag_links)}</p>\n'
    return out


def entry_rows(entries):
    rows = []
    last_date = None
    for e in entries:
        date_cell = e["date"].isoformat() if e["date"] != last_date else ""
        new_day = " sol-new-day" if (e["date"] != last_date and last_date is not None) else ""
        last_date = e["date"]
        cx = complexity_text(e)
        cx_html = f'<span class="sol-cx mono dim">{esc(cx)}</span>' if cx else ""
        rows.append(
            f"""        <tr class="sol-row{new_day}">
          <td class="post-date mono">{date_cell}</td>
          <td class="sol-plat mono dim">{esc(e["platform_short"])}</td>
          <td><a href="/solutions/{e["stem"]}/">{esc(display_title(e))}</a>{difficulty_tag(e)}{cx_html}</td>
        </tr>"""
        )
    return "\n".join(rows)


def list_page(all_entries, shown, path, heading, intro, active=None, crumb=None):
    days = len({e["date"] for e in shown})
    count = f"{len(shown)} problem{'s' if len(shown) != 1 else ''} · {days} day{'s' if days != 1 else ''} · newest first"
    crumb_html = (
        '<a href="/">← rudraansh</a> / solutions'
        if crumb is None
        else f'<a href="/">← rudraansh</a> / <a href="/solutions/">solutions</a> / {esc(crumb)}'
    )

    if shown:
        table = f"""  <div class="mac8 blog-index-table">
    <table class="post-table sol-table">
      <tbody>
{entry_rows(shown)}
      </tbody>
    </table>
  </div>

  <p class="mono dim post-count">{count}</p>
"""
    else:
        table = '  <p class="mono dim sol-empty">No entries yet. First one coming soon.</p>\n'

    filters = filter_bar(all_entries, active) if all_entries else ""

    return (
        head(f"{heading} — Rudraansh Patel", intro, path)
        + GENERATED_NOTE
        + f"""<body class="blog-index">

  <p class="breadcrumb mono">{crumb_html}</p>

  <header class="page-intro">
    <h1>{esc(heading)}</h1>
    <p class="role">{esc(intro)}</p>
  </header>

  <hr />

{filters}{table}
  <hr />

  <p class="mono dim" style="font-size:0.78rem;">
    elsewhere: <a href="/">home</a> &middot; <a href="/projects/">projects</a> &middot; <a href="/blog/">blog</a>
  </p>

</body>
</html>
"""
    )


# ─────────────────────────── detail page ───────────────────────────

def detail_page(e, prev_e, next_e):
    path = f"/solutions/{e['stem']}/"
    meta_bits = [
        f'<time datetime="{e["date"].isoformat()}">{e["date"].strftime("%b %d, %Y")}</time>',
        f'<a href="/solutions/platform/{e["platform_slug"]}/">{esc(e["platform"])}</a>',
    ]
    if e["link"]:
        meta_bits.append(f'<a href="{esc(e["link"])}" target="_blank" rel="noopener">[problem ↗]</a>')

    tags_html = ""
    if e["tags"]:
        tags_html = (
            '\n      <p class="post-meta mono sol-tags">'
            + " · ".join(f'<a href="/solutions/tag/{t}/">{esc(t)}</a>' for t in e["tags"])
            + "</p>"
        )

    complexity = ""
    if e["time"] or e["space"]:
        rows = ""
        if e["time"]:
            rows += f'      <div class="spec-row"><div class="spec-label">Time</div><div class="spec-body"><code>{esc(e["time"])}</code></div></div>\n'
        if e["space"]:
            rows += f'      <div class="spec-row"><div class="spec-label">Space</div><div class="spec-body"><code>{esc(e["space"])}</code></div></div>\n'
        complexity = f"\n    <h2>Complexity</h2>\n{rows}"

    nav = []
    if next_e:
        nav.append(f'<a href="/solutions/{next_e["stem"]}/">← newer</a>')
    nav.append('<a href="/solutions/">all solutions</a>')
    if prev_e:
        nav.append(f'<a href="/solutions/{prev_e["stem"]}/">older →</a>')

    desc = f"{e['platform']} {display_title(e)}: my approach, solution and complexity."

    return (
        head(f"{display_title(e)} — Solutions — Rudraansh Patel", desc, path, og_type="article")
        + GENERATED_NOTE
        + f"""<body class="blog-post">

  <p class="breadcrumb mono"><a href="/">← rudraansh</a> / <a href="/solutions/">solutions</a></p>

  <article class="post sol-post">

    <header class="post-header">
      <h1>{esc(display_title(e))}{difficulty_tag(e)}</h1>
      <p class="post-meta mono">{" · ".join(meta_bits)}</p>{tags_html}
    </header>

{render_md(e["body_md"])}
{complexity}
  </article>

  <hr class="post-end" />

  <p class="mono dim" style="font-size:0.78rem;">
    {" &middot; ".join(nav)}
  </p>

</body>
</html>
"""
    )


# ─────────────────────────── main ───────────────────────────

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    SRC.mkdir(exist_ok=True)
    files = sorted(p for p in SRC.glob("*.md") if not p.name.startswith("_"))

    entries, errors = [], []
    for f in files:
        try:
            entries.append(parse_file(f))
        except ValueError as err:
            errors.append(str(err))
    if errors:
        print("Build failed. Fix these and push again:\n", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}\n", file=sys.stderr)
        sys.exit(1)

    # Same problem logged twice on one day -> suffix -2, -3 ...
    seen = Counter()
    for e in sorted(entries, key=lambda e: e["file"]):
        seen[e["stem"]] += 1
        if seen[e["stem"]] > 1:
            e["stem"] = f'{e["stem"]}-{seen[e["stem"]]}'

    # Newest first.
    entries.sort(key=lambda e: (e["date"], e["stem"]), reverse=True)

    # Rebuild output from scratch so deleted entries disappear.
    if OUT.exists():
        shutil.rmtree(OUT)

    intro = (
        "Problems I solve each day, across platforms. "
        "Each one: the problem in my own words, the approach, the code, and its complexity."
    )
    write(OUT / "index.html", list_page(entries, entries, "/solutions/", "Solutions", intro))

    for i, e in enumerate(entries):
        newer = entries[i - 1] if i > 0 else None
        older = entries[i + 1] if i + 1 < len(entries) else None
        write(OUT / e["stem"] / "index.html", detail_page(e, older, newer))

    platforms = OrderedDict()
    for e in entries:
        platforms.setdefault(e["platform_slug"], (e["platform"], []))[1].append(e)
    for slug, (name, items) in platforms.items():
        write(
            OUT / "platform" / slug / "index.html",
            list_page(entries, items, f"/solutions/platform/{slug}/", f"Solutions · {name}",
                      f"Problems I've solved on {name}.", active=f"p:{slug}", crumb=name),
        )

    tags = OrderedDict()
    for e in entries:
        for t in e["tags"]:
            tags.setdefault(t, []).append(e)
    for t, items in tags.items():
        write(
            OUT / "tag" / t / "index.html",
            list_page(entries, items, f"/solutions/tag/{t}/", f"Solutions · {t}",
                      f"Problems tagged {t}.", active=f"t:{t}", crumb=t),
        )

    print(f"Built {len(entries)} solution(s), {len(platforms)} platform page(s), {len(tags)} tag page(s).")


if __name__ == "__main__":
    main()
