"""Entrypoint for C2M DocGen. Wires together config, the product
registry, the browser, login, and the Scanner. Run as:

    python -m c2m_docgen.run
"""
from datetime import date

from playwright.sync_api import sync_playwright

from .auth import login
from .config import C2MDocGenConfig
from .scanner import run_scan
from .guid_tracker import ProductRegistry
from .manual import init_manual


def main(config: C2MDocGenConfig = None):
    config = config or C2MDocGenConfig()
    run_date = date.today().isoformat()

    registry = ProductRegistry(max_products=config.max_products)
    init_manual(config.output_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        context = browser.new_context(viewport=config.viewport)
        page = context.new_page()

        # diagnostic - log API responses to find where session/product IDs live
        page.on("response", lambda r: registry.on_response(r, config.trusted_id_source_paths))

        login(page, config)
        registry.refresh_from_products_brief(page, config.start_url)

        run_scan(page, config, registry, run_date)

        browser.close()


if __name__ == "__main__":
    main()
