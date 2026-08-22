# codewetrust-document Generator

**C2M DocGen** automatically documents the CodeWeTrust staging dashboard.
It logs in, visits every page and product view, takes a screenshot of
each one (including every tab and sub-tab), and produces a single running
`manual.md` that explains what's on each screen — charts, buttons,
filters, table columns, all of it. Optionally, any individual screenshot
can be handed to Claude to generate a richer, narrative user-manual page
for that specific view.

**What it's for:** keeping an always-up-to-date visual manual of the
dashboard without anyone manually screenshotting and writing docs by
hand. Point it at staging, let it run, and you get a folder of organized
screenshots plus a manual document ready to share.

---

## How it works, in short

1. **Logs in** to the dashboard with credentials from environment variables.
2. **Discovers products** by watching the app's own API calls as pages load
   (no hardcoded product list — it picks up whatever exists today).
3. **Visits every page**, including per-product detail pages, clicking
   through every tab and nested sub-tab along the way.
4. **Screenshots each view** and writes a description of it — charts,
   buttons, filters, table columns, pagination — into `manual.md`.
5. **Organizes output** into one folder per product (named after the
   actual product), so everything is easy to find later.

---

## Requirements

- Python 3.9+
- A CodeWeTrust staging account (username + password)
- (Optional, for AI-generated manual pages) an Anthropic API key

Install dependencies:

```bash
pip install -r requirements.txt
```

This installs `playwright`, `furl`, `requests`, and `anthropic`. Playwright
also needs its browser binaries installed once:

```bash
python -m playwright install chromium
```

---

## Running it

Set your staging credentials as environment variables, then run the
scanner:

```bash
export CWT_USER="you@example.com"
export CWT_PASS="your-password"
python -m c2m_docgen.run
```

A browser window will open (set `headless=True` in the config to run it
invisibly — see below), log in, and start working through the dashboard.
Progress prints to the console as it goes.

### Customizing the run

Everything tunable lives in one config object — no need to edit the code
itself:

```python
from c2m_docgen import C2MDocGenConfig
from c2m_docgen.run import main

main(C2MDocGenConfig(
    max_products=5,      # how many distinct products to crawl (default: 2)
    headless=True,        # run without a visible browser window
    output_dir="my_docs", # where screenshots/manual.md get written
))
```

---

## What you get

```
screenshots/
  manual.md                          # the single combined manual
  2026-08-15_home.png
  2026-08-15_products.png
  tensorflow/                        # one folder per product
    2026-08-15_analyzed-repo.png
    2026-08-15_tech-stack.png
    2026-08-15_tech-stack_charts.png
    2026-08-15_security_vulnerabilities.png
```

Open `manual.md` in anything that renders markdown (VS Code, Obsidian,
GitHub, Typora) and you'll see every screenshot embedded directly next to
a plain-language explanation of what's on it.

---

## Generating a deeper AI manual for one screenshot

Beyond the automatic descriptions, you can ask Claude to write a full,
detailed manual page for any single screenshot — walking through every
button, chart, and control in plain language.

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python -m c2m_docgen.ai_manual
```

This lists every screenshot found, lets you pick one by number, and saves
Claude's write-up as a sibling file next to the image, e.g.:

```
2026-08-15_tech-stack.png  ->  2026-08-15_tech-stack.ai-manual.md
```

To skip the picker and target a specific file directly:

```python
from c2m_docgen.ai_manual import main
main(image_path="screenshots/tensorflow/2026-08-15_tech-stack.png")
```

---

## Project layout

| File | Responsibility |
|---|---|
| `config.py` | All tunable settings (`C2MDocGenConfig`) |
| `scanner.py` | The Scanner — the site-scan loop itself |
| `guid_tracker.py` | Tracks discovered products and resolved names |
| `naming.py` | URL → filename/folder logic (no browser needed) |
| `page_facts.py` | Reads the live page: charts, buttons, filters, etc. |
| `manual.py` | Builds `manual.md` |
| `screenshot.py` | Takes screenshots, handles tab/sub-tab clicking |
| `ai_manual.py` | Sends a screenshot to Claude for a detailed write-up |
| `auth.py` | Login |
| `run.py` | Entrypoint — wires everything together |

---

## Known limitations

- Product-name resolution depends on the shape of `/api/products/brief`'s
  response — if names aren't showing up in folder names, check the
  console output for `Resolved N product name(s)...`.
- The login button selector is an auto-generated CSS class and may need
  updating if the login page changes.
- `/product/{id}` (singular route) has consistently returned an error in
  testing and may not be a real page — worth confirming and removing if so.
