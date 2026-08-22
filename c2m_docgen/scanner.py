"""The Scanner: the BFS site-scan loop itself. Depends on naming/screenshot/
page_facts for the actual per-page work, and on a ProductRegistry for
GUID/product-name state, but doesn't own any of that logic itself.
"""
import time
import urllib.parse
import urllib.robotparser
from collections import deque

from furl import furl

from .naming import build_output_paths
from .page_facts import get_page_heading, wait_for_content_ready
from .screenshot import capture_tabs_if_present, save_screenshot_with_description


def same_origin(a, b):
    return furl(a).origin == furl(b).origin


def load_robots(start_url):
    """Best-effort robots.txt load. Returns a RobotFileParser that
    allows everything if the fetch fails."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(start_url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass
    return rp


def run_scan(page, config, registry, run_date):
    """Runs the full BFS scan: seeds static routes, does an initial
    /products visit to prime the registry, then processes the queue --
    screenshotting each page (with tab traversal) and following same-origin
    links, picking up newly-discovered product GUIDs as dynamic routes
    along the way."""
    rp = load_robots(config.start_url)

    q = deque()
    visited = set()

    def enqueue_new_dynamic_routes():
        for url in registry.pop_new_dynamic_urls(config.start_url, config.dynamic_route_templates, visited):
            q.append(url)

    for route in config.static_routes:
        q.append(urllib.parse.urljoin(config.start_url, route))
    print(f"Queue size after static route seeding: {len(q)}")

    # Visit /products once now so its API calls fire and populate the registry
    try:
        page.goto(urllib.parse.urljoin(config.start_url, "/products"),
                  wait_until="networkidle", timeout=config.timeout_ms)
    except Exception as e:
        print("products page visit failed:", e)

    enqueue_new_dynamic_routes()

    while q and len(visited) < config.max_pages:
        url = q.popleft().split("#")[0]
        if url in visited:
            continue
        if not same_origin(config.start_url, url):
            continue
        try:
            if not rp.can_fetch("*", url):
                print("robots disallow", url)
                visited.add(url)
                continue
        except Exception:
            pass

        try:
            print("Visiting:", url)
            try:
                page.goto(url, wait_until="networkidle", timeout=config.timeout_ms)
            except Exception:
                # networkidle never resolved -- likely continuous polling/websocket
                # traffic on this page. Check if we still landed on the right
                # page before giving up entirely.
                current = page.url.split("#")[0].rstrip("/")
                target = url.rstrip("/")
                if current == target:
                    print("networkidle timed out but page loaded anyway, continuing:", url)
                    page.wait_for_timeout(2000)  # give the UI a moment to settle
                else:
                    raise
        except Exception as e:
            print("goto failed:", url, e)
            visited.add(url)
            continue

        # screenshot (click through tabs if present, otherwise single shot)
        try:
            # wait here too, BEFORE checking for tabs -- otherwise a page
            # whose tab nav hasn't rendered yet gets misread as "no tabs"
            wait_for_content_ready(page)
            subdir, base_filename = build_output_paths(url, run_date, registry.guid_to_name)
            handled = capture_tabs_if_present(page, config.output_dir, subdir, run_date)
            if not handled:
                heading = get_page_heading(page) or url
                save_screenshot_with_description(page, config.output_dir, subdir, base_filename, title=heading)
        except Exception as e:
            print("screenshot failed:", url, e)

        visited.add(url)

        # pick up any new GUIDs this page's API calls revealed
        enqueue_new_dynamic_routes()

        # extract links
        try:
            anchors = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for href in set(anchors):
                if not href:
                    continue
                norm = urllib.parse.urljoin(url, href.split("#")[0])
                if norm not in visited and same_origin(config.start_url, norm):
                    q.append(norm)
        except Exception as e:
            print("extract links failed:", url, e)

        time.sleep(config.delay_seconds)

    print("Done. Pages saved:", len(visited))
    return visited
