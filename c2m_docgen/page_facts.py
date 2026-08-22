"""Everything about inspecting the live page state: waiting for it to
actually be ready, pulling a human-readable heading, and scanning the DOM
for structured facts (charts, buttons, filters, table columns,
pagination) that drive the auto-generated manual.
"""


def wait_for_content_ready(page, extra_ms=800):
    """networkidle only means 'no network requests for a moment' -- it does
    NOT mean the UI has finished rendering. Ant Design pages commonly show
    a spinner (.ant-spin-spinning) while data loads in, then charts animate
    in afterward. This waits for any visible spinner to clear, waits for
    the network to go quiet again (covers AJAX triggered by a tab click),
    then adds a short fixed buffer for chart/transition animations to
    finish. Called right before every screenshot -- initial page load and
    every tab/LHN click."""
    try:
        page.wait_for_selector(".ant-spin-spinning", state="detached", timeout=8000)
    except Exception:
        pass  # no spinner appeared, or it never cleared in time -- proceed anyway
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(extra_ms)


def get_page_heading(page):
    """Best-effort extraction of a visible page/section heading, so the
    description has something more human than a raw URL when no tab
    label is available."""
    for selector in ["h1", "h2", ".ant-page-header-heading-title", ".ant-typography h1"]:
        el = page.query_selector(selector)
        if el:
            try:
                text = el.inner_text().strip()
                if text:
                    return text
            except Exception:
                continue
    return None


def collect_page_facts(page):
    """Scans the currently active view (scoped to the innermost active tab
    panel, if any) and returns a structured dict of what's on screen:
    charts, buttons (export vs other), date filters, dropdown filters,
    table columns/filterability, and pagination. This is the single
    source of truth used to build each manual.md section."""

    active_panes = page.query_selector_all(".ant-tabs-tabpane-active")
    scope = active_panes[-1] if active_panes else page  # innermost active pane, if nested

    facts = {
        "charts": [],
        "export_labels": [],
        "other_labels": [],
        "date_filter_count": 0,
        "dropdown_labels": [],
        "filterable_column_count": 0,
        "table_columns": [],
        "pagination": None,  # dict with total_pages / page_size, or None
    }

    # --- Charts (Highcharts) ---
    try:
        chart_wrappers = scope.query_selector_all("div[id]")
        seen_titles = set()
        for w in chart_wrappers:
            try:
                if w.query_selector(".highcharts-container") is None:
                    continue
                wid = (w.get_attribute("id") or "").strip()
                if not wid:
                    continue
                # ids look like "tensorflow - Tech Stack Pie Chart" -- product prefix + title
                title = wid.split(" - ", 1)[-1].strip() if " - " in wid else wid
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                chart_type = "chart"
                svg = w.query_selector("svg")
                if svg:
                    html = svg.inner_html()
                    if "highcharts-pie-series" in html:
                        chart_type = "pie chart"
                    elif "highcharts-line-series" in html:
                        chart_type = "line chart"
                    elif "highcharts-column-series" in html:
                        chart_type = "bar chart"
                    elif "highcharts-area-series" in html:
                        chart_type = "area chart"
                facts["charts"].append({"title": title, "type": chart_type})
            except Exception:
                continue
    except Exception:
        pass

    # --- Buttons -- split into export/save actions vs everything else ---
    try:
        buttons = scope.query_selector_all("button, .ant-btn")
        labels = []
        for b in buttons:
            try:
                text = b.inner_text().strip()
                if not text:
                    # icon-only buttons (e.g. "Show/hide columns") have no
                    # visible text -- fall back to their title attribute
                    title_attr = b.get_attribute("title")
                    if title_attr:
                        text = title_attr.strip()
                if text and text not in labels and len(text) < 60:
                    labels.append(text)
            except Exception:
                continue

        facts["export_labels"] = [l for l in labels if any(k in l.lower() for k in ["export", "save", "download"])]
        facts["other_labels"] = [l for l in labels if l not in facts["export_labels"]]
    except Exception:
        pass

    # --- Date range filters ---
    try:
        facts["date_filter_count"] = len(scope.query_selector_all(".ant-picker-range"))
    except Exception:
        pass

    # --- Dropdown filters ---
    try:
        selects = scope.query_selector_all(".ant-select-selector, select")
        labels = []
        for s in selects:
            try:
                text = s.inner_text().strip()
                labels.append(text if text else "an unlabeled dropdown")
            except Exception:
                continue
        facts["dropdown_labels"] = labels
    except Exception:
        pass

    # --- Filterable/sortable table columns ---
    try:
        facts["filterable_column_count"] = len(scope.query_selector_all(".ant-table-filter-trigger"))
    except Exception:
        pass

    try:
        columns = scope.query_selector_all(".ant-table-column-title")
        col_labels = []
        for c in columns:
            try:
                text = c.inner_text().strip()
                if text and text not in col_labels:
                    col_labels.append(text)
            except Exception:
                continue
        facts["table_columns"] = col_labels
    except Exception:
        pass

    # --- Pagination ---
    try:
        pagination = scope.query_selector(".ant-pagination")
        if pagination:
            page_numbers = []
            for item in scope.query_selector_all(".ant-pagination-item"):
                t = item.get_attribute("title")
                if t and t.isdigit():
                    page_numbers.append(int(t))
            page_size_el = scope.query_selector(".ant-pagination-options-size-changer .ant-select-selection-item")
            page_size_text = None
            if page_size_el:
                page_size_text = page_size_el.get_attribute("title") or page_size_el.inner_text().strip()
            facts["pagination"] = {
                "total_pages": max(page_numbers) if page_numbers else None,
                "page_size": page_size_text,
            }
    except Exception:
        pass

    return facts
