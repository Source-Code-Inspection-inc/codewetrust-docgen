"""Replaces the old module-level globals (captured_ids, GUID_TO_NAME,
queued_ids) with a single explicit object. Passing this around instead of
relying on globals makes it possible to construct a fresh, isolated
registry per test (or per concurrent scan, if that's ever needed) without
state leaking between them.
"""
import urllib.parse

from .naming import GUID_PATTERN, build_guid_name_map


class ProductRegistry:
    """Tracks every product GUID discovered during a run, the best-known
    name for each, and which GUIDs have already been turned into queued
    dynamic-route URLs (capped at max_products)."""

    def __init__(self, max_products):
        self.max_products = max_products
        self.captured_ids = set()
        self.queued_ids = set()
        self.broken_ids = set()
        self.guid_to_name = {}

    def mark_broken(self, gid):
        """Flags a product GUID as broken (its page showed an error
        notification -- e.g. a deleted/orphaned scan session) so
        pop_new_dynamic_urls stops counting it against max_products,
        freeing its slot for a working replacement instead."""
        self.broken_ids.add(gid)

    def add_ids_from_text(self, text, source_label, source_url=""):
        """Scans arbitrary text (a URL or a response body) for GUIDs and
        records any new ones. Returns the list of newly-seen GUIDs."""
        new_ids = []
        for match in GUID_PATTERN.findall(text):
            if match not in self.captured_ids:
                self.captured_ids.add(match)
                new_ids.append(match)
                print(f"Captured new ID (from {source_label}):", match, "from", source_url)
        return new_ids

    def update_names(self, body_text):
        """Merges any product name mappings found in body_text (a JSON
        response body) into the registry."""
        self.guid_to_name.update(build_guid_name_map(body_text))

    def refresh_from_products_brief(self, page, start_url):
        """Explicitly (re-)fetches /api/products/brief using the browser's
        authenticated session, guaranteeing captured_ids/guid_to_name
        reflect TODAY's live data before any dynamic routes are queued --
        we never cache or reuse GUIDs from a previous run/day, and we don't
        rely on page-navigation timing to happen to trigger this call."""
        print("Refreshing product GUID list for this run...")
        try:
            resp = page.request.get(urllib.parse.urljoin(start_url, "/api/products/brief"))
        except Exception as e:
            print(f"  Explicit GUID refresh failed ({e}); falling back to page-navigation capture.")
            return

        if not resp.ok:
            print(f"  /api/products/brief returned {resp.status}; falling back to page-navigation capture.")
            return

        body = resp.text()
        new_ids = self.add_ids_from_text(body, source_label="brief-fetch")
        self.update_names(body)
        print(f"  Found {len(self.captured_ids)} GUID(s) today ({len(new_ids)} not seen yet this run).")
        print(f"  Resolved {len(self.guid_to_name)} product name(s) for folder names.")

    def on_response(self, response, trusted_id_source_paths):
        """Playwright response-event handler (bind as
        page.on("response", lambda r: registry.on_response(r, config.trusted_id_source_paths))).
        Logs every /api/ call, surfaces error bodies for diagnosis, and
        scans trusted product-list endpoints for new GUIDs/names."""
        if "/api/" not in response.url:
            return

        # Skip endpoints known to return deleted/invalid records -- their
        # IDs 404/400 on every per-product endpoint and have no real
        # dashboard page.
        if "deletedOnly=true" in response.url:
            return

        print(f"API RESPONSE [{response.status}]: {response.url}")

        # For failing per-product endpoints (400/404/etc, excluding the
        # expected 204 "nothing scanning" case), log the response body so
        # the actual error message is visible, not just the status code --
        # key for telling a stale/expired GUID apart from a plain wrong route.
        if response.status not in (200, 204):
            try:
                print(f"    -> body: {response.text()[:500]}")
            except Exception as e:
                print(f"    -> could not read body: {e}")

        if response.status != 200:
            return

        parsed_path = urllib.parse.urlparse(response.url).path.rstrip("/")
        if parsed_path not in trusted_id_source_paths:
            return  # not a product-list endpoint -- don't scan its body for GUIDs/names

        self.add_ids_from_text(response.url, source_label="URL", source_url=response.url)

        try:
            body_text = response.text()
        except Exception:
            return

        self.add_ids_from_text(body_text, source_label="body", source_url=response.url)
        self.update_names(body_text)

    def pop_new_dynamic_urls(self, start_url, dynamic_route_templates, visited):
        """Turns any newly captured GUIDs (not yet queued) into real page
        URLs, up to max_products distinct WORKING GUIDs total -- one
        marked broken (see mark_broken) no longer counts against the cap,
        so the next call here queues a replacement in its place. Returns
        the list of new URLs to enqueue."""
        active_count = len(self.queued_ids - self.broken_ids)
        if active_count >= self.max_products:
            return []

        new_urls = []
        new_ids = self.captured_ids - self.queued_ids
        for gid in new_ids:
            if active_count >= self.max_products:
                break
            for template in dynamic_route_templates:
                path = template.replace("{id}", gid)
                full_url = urllib.parse.urljoin(start_url, path)
                if full_url not in visited:
                    new_urls.append(full_url)
                    print("Queued dynamic route:", full_url)
            self.queued_ids.add(gid)
            active_count += 1

        return new_urls
