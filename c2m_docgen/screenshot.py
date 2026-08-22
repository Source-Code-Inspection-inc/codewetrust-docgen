"""Owns the file-writing side effects: taking a full-page screenshot,
saving it into the right subfolder, and appending a matching section to
manual.md. Also handles clicking through Ant Design tabs/LHN sub-tabs so
each one gets its own screenshot.
"""
import os

from .manual import append_section
from .naming import slugify
from .page_facts import collect_page_facts, wait_for_content_ready


def save_screenshot_with_description(page, out_dir, subdir, filename_base, title):
    """Takes a full-page screenshot and appends a matching section (with
    the image embedded inline) to the running manual.md draft, built from
    collect_page_facts. No separate .txt sidecar -- manual.md is the
    single source of truth for descriptions.

    out_dir is the root screenshots folder (where manual.md always lives).
    subdir is None for site-wide pages (files saved flat in out_dir) or a
    per-product folder name for product-specific pages -- the folder is
    created on demand. The image path written into manual.md is relative
    to manual.md itself (e.g. "tensorflow/2026-08-15_tech-stack.png"), so
    the whole out_dir tree stays portable together."""
    png_filename = f"{filename_base}.png"

    target_dir = os.path.join(out_dir, subdir) if subdir else out_dir
    os.makedirs(target_dir, exist_ok=True)

    png_path = os.path.join(target_dir, png_filename)
    # forward slashes always, regardless of OS, so links work in any markdown viewer
    image_rel_path = f"{subdir}/{png_filename}" if subdir else png_filename

    wait_for_content_ready(page)
    page.screenshot(path=png_path, full_page=True)

    facts = collect_page_facts(page)
    append_section(out_dir, title, page.url, image_rel_path, facts)

    print("Saved:", png_path)
    return png_path


def capture_tabs_if_present(page, out_dir, subdir, run_date):
    """Handles Ant Design tabs, including the nested pattern seen here:
    top-level tabs (Tech Stack, Dev Team, Security...) each containing a
    vertical LHN sub-menu built from the same tabs component. Clicks every
    top tab, then every LHN item inside it, screenshotting each
    combination. Falls back to a single screenshot if no tabs exist, and
    to a per-top-tab screenshot if a top tab has no nested LHN.

    Returns True if any tab-based screenshot was taken (caller should skip
    its own fallback screenshot), False if no tabs were found at all."""

    top_nav = page.query_selector(".ant-tabs-nav-list")
    if not top_nav:
        return False

    top_tabs = top_nav.query_selector_all(":scope > .ant-tabs-tab")
    top_count = len(top_tabs)
    if top_count == 0:
        return False

    print(f"Found {top_count} top-level tabs")

    for i in range(top_count):
        try:
            # re-query top nav/tabs each time -- Ant Design may re-render after a click
            top_nav = page.query_selector(".ant-tabs-nav-list")
            current_top_tabs = top_nav.query_selector_all(":scope > .ant-tabs-tab")
            if i >= len(current_top_tabs):
                break
            top_tab = current_top_tabs[i]
            top_label = top_tab.inner_text().strip() or f"tab{i+1}"
            top_tab.click()
            wait_for_content_ready(page, extra_ms=500)  # let the panel (and its LHN) actually render
            safe_top = slugify(top_label, maxlen=30)

            # look for a nested LHN tab-list inside the now-active panel
            active_nav = page.query_selector(".ant-tabs-tabpane-active .ant-tabs-nav-list")

            if not active_nav:
                # no LHN under this tab -- just screenshot the tab itself
                filename_base = f"{run_date}_{safe_top}"
                save_screenshot_with_description(page, out_dir, subdir, filename_base, title=top_label)
                continue

            lhn_tabs = active_nav.query_selector_all(":scope > .ant-tabs-tab")
            lhn_count = len(lhn_tabs)
            print(f"  Found {lhn_count} LHN items under '{top_label}'")

            for j in range(lhn_count):
                try:
                    active_nav = page.query_selector(".ant-tabs-tabpane-active .ant-tabs-nav-list")
                    current_lhn_tabs = active_nav.query_selector_all(":scope > .ant-tabs-tab")
                    if j >= len(current_lhn_tabs):
                        break
                    lhn_tab = current_lhn_tabs[j]
                    lhn_label = lhn_tab.inner_text().strip() or f"item{j+1}"
                    lhn_tab.click()
                    wait_for_content_ready(page, extra_ms=500)
                    safe_lhn = slugify(lhn_label, maxlen=30)
                    filename_base = f"{run_date}_{safe_top}_{safe_lhn}"
                    save_screenshot_with_description(
                        page, out_dir, subdir, filename_base,
                        title=f"{top_label} > {lhn_label}"
                    )
                except Exception as e:
                    print("  LHN click/screenshot failed:", e)

        except Exception as e:
            print("Top tab click/screenshot failed:", e)

    return True
