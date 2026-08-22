"""All tunable scanner settings live here as a single dataclass, instead of
loose module-level constants. This makes it possible to point C2M DocGen
at a different environment/site by constructing a different
C2MDocGenConfig, rather than editing the script -- and it's trivially
passed around instead of relying on module globals.
"""
import os
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class C2MDocGenConfig:
    # --- site / auth ---
    start_url: str = "https://staging-internal.codewetrust-api.com/"
    login_url: str = "https://staging-internal.codewetrust-api.com/login"
    logged_in_check_selector: str = "a[href='/logout']"
    username: str = field(default_factory=lambda: os.environ.get("CWT_USER"))
    password: str = field(default_factory=lambda: os.environ.get("CWT_PASS"))
    # Selector is brittle (auto-generated CSS module classes) -- if login
    # ever breaks, this is the first thing to re-check via the browser's
    # inspector, or just rely on the Enter-key fallback in auth.login().
    submit_selector: str = (
        "#basic > div:nth-child(4) > div > div > div > div > div "
        "> div.ant-col.ant-col-10.css-3qoecq > button"
    )

    # --- scan behavior ---
    output_dir: str = "screenshots"
    max_pages: int = 1000
    max_products: int = 2  # cap how many distinct product GUIDs get scanned
    delay_seconds: float = 0.5
    timeout_ms: int = 30000
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    headless: bool = False

    # --- routes ---
    static_routes: List[str] = field(default_factory=lambda: [
        "/",
        "/add-product",
        "/products",
        "/settings",
        "/profile",
    ])
    # {id} gets replaced with each discovered product GUID. Only
    # single-GUID routes are handled automatically; routes needing more
    # than one param (e.g. GROUP_SESSIONS, NEW_PROJECT) aren't supported
    # here -- add them manually if you can source the extra values.
    dynamic_route_templates: List[str] = field(default_factory=lambda: [
        "/analyzed-repository/{id}",
        "/product/{id}",
    ])

    # Only these endpoints are trusted as sources of product-list GUIDs.
    # Per-product detail/report endpoints (CodeRisks, LicenseReport, files,
    # etc.) return item-level GUIDs (individual files, risks, license rows)
    # that are NOT product IDs, and scanning them just creates noise.
    trusted_id_source_paths: Set[str] = field(
        default_factory=lambda: {"/api/products", "/api/products/brief"}
    )
