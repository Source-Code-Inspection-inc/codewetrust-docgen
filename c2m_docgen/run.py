"""Entrypoint for C2M DocGen. Wires together config, the product
registry, the browser, login, and the Scanner. Run as:

    python -m c2m_docgen.run
"""
import argparse

from playwright.sync_api import sync_playwright

from .auth import login
from .config import C2MDocGenConfig
from .scanner import run_scan, run_single_product_scan
from .guid_tracker import ProductRegistry
from .manual import init_manual


def main(config: C2MDocGenConfig = None, product_name: str = None):
    """If product_name is given, scans only that one product (skipping it
    entirely if it's deleted/not found) instead of doing the full BFS
    site scan."""
    config = config or C2MDocGenConfig()

    registry = ProductRegistry(max_products=config.max_products)
    init_manual(config.output_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        context = browser.new_context(viewport=config.viewport)
        page = context.new_page()

        # diagnostic - log API responses to find where session/product IDs live
        page.on("response", lambda r: registry.on_response(r, config.trusted_id_source_paths))

        login(page, config)

        if product_name:
            run_single_product_scan(page, config, registry, product_name)
        else:
            registry.refresh_from_products_brief(page, config.start_url)
            run_scan(page, config, registry)

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--product",
        help="Scan only this single product by name (skipped if it's deleted or not found), "
             "instead of doing the full site scan.",
    )
    args = parser.parse_args()
    main(product_name=args.product)
