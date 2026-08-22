"""Login flow, isolated from the Scanner and naming logic."""


def login(page, config):
    """Logs into config.login_url using config.username/password. The
    submit_selector is brittle (auto-generated CSS module classes) --
    falls back to pressing Enter in the password field if the button
    selector doesn't match."""
    print("Opening login page...")
    page.goto(config.login_url, wait_until="networkidle", timeout=config.timeout_ms)
    page.screenshot(path="debug_login.png", full_page=True)
    page.fill("#basic_email", config.username)
    page.fill("input[type='password']", config.password)

    if page.locator(config.submit_selector).count() > 0:
        page.click(config.submit_selector)
    else:
        page.press("input[type='password']", "Enter")

    try:
        page.wait_for_selector(config.logged_in_check_selector, timeout=10000)
        print("Logged in")
    except Exception:
        print("Logged-in indicator not found; continuing anyway")

    # Optionally save auth state:
    # page.context.storage_state(path="auth_state.json")
