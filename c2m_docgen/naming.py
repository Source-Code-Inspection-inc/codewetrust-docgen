"""Everything about turning a URL (+ known product names) into a filesystem
path is pure logic with no Playwright dependency, so it lives here and can
be unit-tested with plain strings/dicts -- no browser required.

Naming scheme: filenames are "{page-type}" for a site-wide plain page, or
"{product-name}_{page-type}" for a product page, or "{tab-slug}" /
"{tab-slug}_{lhn-slug}" once inside a specific tab (see
screenshot.capture_tabs_if_present) -- no date is embedded anywhere, so
reruns overwrite same-named files rather than accumulating by day.
Screenshots for product-specific pages are grouped into a subfolder named
after the PRODUCT (e.g. screenshots/tensorflow/...); site-wide pages
(home, /products, /settings, etc.) are saved flat in the root of the
output dir.
"""
import json
import re
import urllib.parse

GUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

# (page-type, path-regex, has_guid) -- matched in order against the URL path
ROUTE_PATTERNS = [
    ("home", re.compile(r"^/$"), False),
    ("add-product", re.compile(r"^/add-product$"), False),
    ("products", re.compile(r"^/products$"), False),
    ("settings", re.compile(r"^/settings$"), False),
    ("profile", re.compile(r"^/profile$"), False),
    ("analyzed-repo", re.compile(r"^/analyzed-repository/(?P<id>[0-9a-fA-F-]{36})$"), True),
    ("product-detail", re.compile(r"^/product/(?P<id>[0-9a-fA-F-]{36})$"), True),
]


def slugify(text, maxlen=40):
    """Turns arbitrary text into a short, filename-safe, lowercase slug."""
    text = re.sub(r"[^0-9A-Za-z]+", "-", str(text)).strip("-").lower()
    return text[:maxlen] or "untitled"


def _squash_tab(text):
    """First letter capitalized, rest lowercased, separators stripped --
    e.g. "Tech Stack" -> "Techstack". Used only in the per-product
    screenshot filename (see build_screenshot_filename), not in folder
    names (which still go through slugify)."""
    cleaned = re.sub(r"[^0-9A-Za-z]+", "", str(text))
    return (cleaned[0].upper() + cleaned[1:].lower()) if cleaned else "Tab"


def _squash_lhn(text):
    """Fully lowercased, separators stripped -- e.g. "Bug Spot" -> "bugspot"."""
    cleaned = re.sub(r"[^0-9A-Za-z]+", "", str(text))
    return cleaned.lower() or "overview"


def build_screenshot_filename(product_name, tab_name, lhn_name, ext="png"):
    """Naming scheme for per-product tab/LHN screenshots:
    "Product-{product_name}-{TabSlug}-{lhn_slug}[.ext]", e.g.
        build_screenshot_filename("openCode", "Tech Stack", "Charts")
          -> "Product-openCode-Techstack-charts.png"
    product_name is used AS-IS (not slugified) so it preserves the
    product's real display casing (e.g. "openCode") -- only the tab/LHN
    portions get squashed. Pass ext=None to get the name with no
    extension (screenshot.py appends ".png" itself)."""
    base = f"Product-{product_name}-{_squash_tab(tab_name)}-{_squash_lhn(lhn_name)}"
    return f"{base}.{ext}" if ext else base


def classify_route(url):
    """Maps a URL to (page_type, guid_or_None) using ROUTE_PATTERNS, falling
    back to a slugified version of the raw path for anything unrecognized
    (e.g. a route discovered via link-following that isn't in
    config.static_routes or config.dynamic_route_templates)."""
    path = urllib.parse.urlparse(url).path.rstrip("/") or "/"
    for page_type, pattern, has_guid in ROUTE_PATTERNS:
        m = pattern.match(path)
        if m:
            return page_type, (m.group("id") if has_guid else None)
    return slugify(path), None


def _normalize_guid(raw_id):
    """Product IDs from the API can be prefixed to distinguish product
    types (e.g. "p-000c0000-...-08def83bed47" for a product, "pg-..."
    for a product group), but URLs/routes only ever contain the BARE
    GUID with no prefix. If keys in guid_to_name keep the prefix, a
    lookup by the URL-extracted GUID never matches -- every product then
    silently falls into the unknown-product-{tail} fallback. This
    extracts just the embedded GUID, regardless of any prefix, so both
    sides always agree."""
    m = GUID_PATTERN.search(str(raw_id))
    return m.group(0).lower() if m else None


def build_guid_name_map(body_text):
    """Best-effort parse of a /api/products or /api/products/brief JSON
    body into {lowercase_guid: product_name}. Tries a handful of common
    field name variants since the exact schema isn't confirmed. Returns {}
    on any parse failure rather than raising -- this is a naming nicety,
    not something that should ever break the scan."""
    mapping = {}
    try:
        data = json.loads(body_text)
    except Exception:
        return mapping

    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or data.get("products") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    id_keys = ("id", "Id", "ID", "productId", "ProductId", "guid", "Guid")
    name_keys = ("name", "Name", "productName", "ProductName", "title", "Title")

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_id = next((item[k] for k in id_keys if k in item and item[k]), None)
        name = next((item[k] for k in name_keys if k in item and item[k]), None)
        if not (raw_id and name):
            continue
        gid = _normalize_guid(raw_id)
        if gid:
            mapping[gid] = str(name)

    return mapping


def build_output_paths(url, guid_to_name):
    """Builds (subdir, filename_base, product_name) for a page about to be
    screenshotted.

    subdir is None for site-wide pages (saved flat in the output root) or
    the slugified PRODUCT NAME for product-specific pages -- falls back to
    "unknown-product-{guid-tail}" if the name can't be resolved yet, so
    folders are still unique and traceable back to the GUID even without
    a name.

    product_name is the RAW (unslugified) resolved display name, or None
    if this isn't a product page or the name isn't known yet. Callers
    (capture_tabs_if_present) use this -- not subdir -- to build the
    Product-<name>-<tab>-<lhn> filename, so a product's real casing
    (e.g. "openCode") is preserved in filenames even though the folder
    name itself is lowercase-slugified.

    filename_base is "{product_name}_{page_type}" once the product name is
    known, or just "{page_type}" for site-wide pages (or product pages
    whose name isn't resolved yet -- the containing "unknown-product-*"
    folder still keeps it unique). capture_tabs_if_present rewrites this
    further for tabbed views, dropping page-type entirely once we're
    inside a specific tab.
    """
    page_type, gid = classify_route(url)

    product_name = None
    if gid:
        product_name = guid_to_name.get(gid.lower())
        if product_name:
            subdir = slugify(product_name, maxlen=50)
        else:
            # Use the LAST hex group, not the first -- in this app's data
            # most GUIDs share the same first group (e.g.
            # "000c0000-6e13-0646-..."), so a first-group-only fallback
            # would collide across products. The last group actually varies.
            guid_tail = gid.split("-")[-1]
            subdir = f"unknown-product-{guid_tail}"
    else:
        subdir = None

    filename_base = f"{product_name}_{page_type}" if product_name else page_type

    return subdir, filename_base, product_name
