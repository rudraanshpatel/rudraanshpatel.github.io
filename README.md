# rudraanshpatel.github.io

Source for [rudraanshpatel.in](https://rudraanshpatel.in) — my personal
site. Hand-written HTML/CSS, no framework, no build step. Hosted on
GitHub Pages.

## Design

Document-first. Reads like a printed page:

- Warm grey paper background, Georgia serif body
- Classic blue underlined links with a yellow highlighter on hover
- Monospace (Courier New) for dates, tags, and meta
- GCC-style layout — wide intro, two content columns, narrow right
  sidebar with blue heading bars
- Chunky Mac OS 8 scrollbars on bounded scroll widgets (signature touch)

All visual tokens live as CSS variables at the top of `style.css`.

## Files

| File              | Purpose                                            |
|-------------------|----------------------------------------------------|
| `index.html`      | Homepage                                           |
| `style.css`       | Shared stylesheet for all pages                    |
| `404.html`        | Custom 404 + LeetCode redirect (see below)         |
| `problems.json`   | Index of LeetCode problems (id, slug, title, premium flag) |
| `CNAME`           | Custom-domain config for GitHub Pages              |

## LeetCode redirect at `/<problem-number>`

Visiting `rudraanshpatel.in/1` redirects to the LeetCode page for
problem 1. The mechanism:

1. GitHub Pages serves `404.html` for any unknown path.
2. `404.html` parses the path; if it's a number, it fetches
   `/problems.json`.
3. If the problem is free, it redirects to
   `leetcode.com/problems/<slug>/description/`.
4. If the problem is premium, it shows a small chooser with two
   buttons — Open on LeetCode or Search on Google.
5. Anything that isn't a number falls back to a normal 404.

`problems.json` is updated periodically.

## Local preview

Static files — open `index.html` directly in a browser, or serve the
folder:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

For the `/<number>` redirect to work locally you need to be on a server
(not `file://`) because `404.html` fetches `problems.json`.

## Stack

HTML · CSS · vanilla JS · GitHub Pages.

## License

MIT for the code. Content (writing, project descriptions, photos)
is © Rudraansh Patel, all rights reserved.