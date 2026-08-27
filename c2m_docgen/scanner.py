"""The Scanner: the BFS site-scan loop itself. Depends on naming/screenshot/
page_facts for the actual per-page work, and on a ProductRegistry for
GUID/product-name state, but doesn't own any of that logic itself.
"""
import os
import time
import urllib.parse
import urllib.robotparser
from collections import deque

from furl import furl

from .naming import build_output_paths, classify_route, slugify
from .page_facts import get_page_heading, page_has_error_notification, wait_for_content_ready
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


def run_scan(page, config, registry):
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

        # Skip other routes for a product already known to be broken (its
        # OTHER dynamic-route URL already showed an error notification --
        # see the mark_broken call below) rather than spending a second
        # network round-trip confirming what we already know.
        _, url_gid = classify_route(url)
        if url_gid and url_gid.lower() in registry.broken_ids:
            print("Skipping known-broken product route:", url)
            visited.add(url)
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

            gid = url_gid
            if page_has_error_notification(page):
                # Orphaned product: its card is still listed but the scan
                # session it points to was deleted server-side, so the
                # page shows "Resource not found" / "Scan session not
                # found" instead of real content. Skip screenshotting it
                # and, if it's a product page, free its max_products slot
                # (see ProductRegistry.mark_broken) so a working product
                # gets scanned in its place instead.
                print("Error notification on page, skipping screenshot:", url)
                if gid:
                    registry.mark_broken(gid.lower())
            else:
                # A GUID can reach the queue via a trusted list endpoint that
                # only carries the ID, not the name (e.g. discovered mid-crawl
                # before /api/products/brief's name mapping covers it) -- that
                # used to fall back to an "unknown-product-{guid-tail}" folder
                # for the rest of the run. Get the name BEFORE building output
                # paths: fall back to the page's own heading, which is usually
                # the product name on these detail pages.
                if gid and gid.lower() not in registry.guid_to_name:
                    heading = get_page_heading(page)
                    if heading:
                        registry.guid_to_name[gid.lower()] = heading

                subdir, base_filename, product_name = build_output_paths(url, registry.guid_to_name)
                handled = capture_tabs_if_present(page, config.output_dir, subdir, product_name=product_name)
                if not handled:
                    heading = get_page_heading(page) or url
                    save_screenshot_with_description(page, config.output_dir, subdir, base_filename, title=heading)
        except Exception as e:
            print("screenshot failed:", url, e)

        visited.add(url)

        # pick up any new GUIDs this page's API calls revealed (also
        # backfills the slot freed by mark_broken above, if any)
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


def run_single_product_scan(page, config, registry, product_name):
    """Scans ONE product end-to-end instead of the full site.

    Deleted-product check: refresh_from_products_brief() re-fetches
    /api/products/brief, which (per the existing on_response filtering
    for deletedOnly=true elsewhere in this codebase) only ever returns
    CURRENTLY ACTIVE products. So if product_name isn't present in
    registry.guid_to_name after this refresh, it's either deleted, was
    renamed, or never existed -- either way, we stop here and no folder
    gets created.

    On success: navigates straight to the product's detail page (first
    matching template in config.dynamic_route_templates), then walks its
    tabs/LHN via capture_tabs_if_present, saving everything into a folder
    named after the product using the Product-<name>-<tab>-<lhn> naming
    scheme (see naming.build_screenshot_filename).

    Returns the output folder path, or None if the product wasn't found/
    was deleted.
    """
    registry.refresh_from_products_brief(page, config.start_url)

    gid = next((g for g, name in registry.guid_to_name.items() if name == product_name), None)
    if not gid:
        print(f"'{product_name}' not found in the active product list "
              f"(deleted, renamed, or misspelled) -- skipping scan, no folder created.")
        return None

    template = config.dynamic_route_templates[0]
    url = urllib.parse.urljoin(config.start_url, template.replace("{id}", gid))

    print(f"Scanning single product '{product_name}' at {url}")
    try:
        page.goto(url, wait_until="networkidle", timeout=config.timeout_ms)
    except Exception as e:
        print("goto failed:", url, e)
        return None

    wait_for_content_ready(page)

    subdir = slugify(product_name, maxlen=50)
    handled = capture_tabs_if_present(page, config.output_dir, subdir, product_name=product_name)
    if not handled:
        heading = get_page_heading(page) or product_name
        save_screenshot_with_description(page, config.output_dir, subdir, f"{product_name}_overview", title=heading)

    out_folder = os.path.join(config.output_dir, subdir)
    print("Done. Screenshots saved to:", out_folder)
    return out_folder
