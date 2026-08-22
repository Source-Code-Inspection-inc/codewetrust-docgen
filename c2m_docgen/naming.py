"""Everything about turning a URL (+ known product names) into a filesystem
path is pure logic with no Playwright dependency, so it lives here and can
be unit-tested with plain strings/dicts -- no browser required.

Naming scheme: filenames are "{date}_{page-type}" for a plain page, or
"{date}_{tab-slug}" / "{date}_{tab-slug}_{lhn-slug}" once inside a specific
tab (see screenshot.capture_tabs_if_present). Screenshots for
product-specific pages are grouped into a subfolder named after the
PRODUCT (e.g. screenshots/tensorflow/...); site-wide pages (home,
/products, /settings, etc.) are saved flat in the root of the output dir.
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


def build_guid_name_map(body_text):
    """Best-effort parse of a /api/products or /api/products/brief JSON body
    into {lowercase_guid: product_name}. Tries a handful of common field
    name variants since the exact schema isn't confirmed. Returns {} on any
    parse failure rather than raising -- this is a naming nicety, not
    something that should ever break the scan."""
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
        gid = next((item[k] for k in id_keys if k in item and item[k]), None)
        name = next((item[k] for k in name_keys if k in item and item[k]), None)
        if gid and name:
            mapping[str(gid).lower()] = str(name)

    return mapping


def build_output_paths(url, run_date, guid_to_name):
    """Builds (subdir, filename_base) for a page about to be screenshotted.

    subdir is None for site-wide pages (saved flat in the output root) or
    the PRODUCT NAME (resolved via guid_to_name) for product-specific
    pages -- falls back to "unknown-product-{guid-tail}" if the name can't
    be resolved yet, so folders are still unique and traceable back to the
    GUID even without a name.

    filename_base is just "{run_date}_{page_type}" -- capture_tabs_if_present
    rewrites this further into "{run_date}_{tab-slug}" or
    "{run_date}_{tab-slug}_{lhn-slug}" for tabbed views, dropping page-type
    entirely once we're inside a specific tab.
    """
    page_type, gid = classify_route(url)

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

    filename_base = f"{run_date}_{page_type}"

    return subdir, filename_base
