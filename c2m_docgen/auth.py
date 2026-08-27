"""Login flow, isolated from the Scanner and naming logic."""


def login(page, config):
    """Logs into config.login_url using config.username/password. The
    submit_selector is brittle (auto-generated CSS module classes) --
    falls back to pressing Enter in the password field if the button
    selector doesn't match.

    Emits extra diagnostics (credentials presence, which submit path was
    taken, URL before/after) specifically so that a failed login prints
    enough to pinpoint WHERE it broke, instead of just "didn't work"."""
    print("Opening login page...")
    page.goto(config.login_url, wait_until="networkidle", timeout=config.timeout_ms)
    page.screenshot(path="debug_login_before.png", full_page=True)
    print(f"  Landed on: {page.url}")

    if not config.username or not config.password:
        print("  WARNING: CWT_USER and/or CWT_PASS environment variable is not set "
              "(config.username/password is None/empty) -- fields will be filled "
              "with an empty string or the literal text 'None'.")

    email_count = page.locator("#basic_email").count()
    pw_count = page.locator("input[type='password']").count()
    print(f"  Email field found: {email_count > 0} | Password field found: {pw_count > 0}")
    if email_count == 0 or pw_count == 0:
        print("  Login form fields not found -- login_url may have changed, "
              "or the page redirected somewhere unexpected before this point.")

    page.fill("#basic_email", config.username or "")
    page.fill("input[type='password']", config.password or "")

    if page.locator(config.submit_selector).count() > 0:
        print("  Submitting via button click (submit_selector matched).")
        page.click(config.submit_selector)
    else:
        print("  submit_selector did NOT match anything on this page -- "
              "falling back to pressing Enter. If this is new, the login "
              "page's markup/CSS-module classes likely changed; re-inspect "
              "and update config.submit_selector.")
        page.press("input[type='password']", "Enter")

    # The button showed a loading spinner in the last run, confirming the
    # click DID fire a request -- so the open question is whether that
    # request succeeded (and just didn't redirect/URL didn't change) or
    # failed outright (bad credentials, expired staging account, etc).
    # Race an error-message appearing against the URL actually leaving
    # /login, instead of a blind fixed sleep, so we can tell which one
    # happened instead of just timing out uninformatively.
    error_selector = (
        ".ant-message-error, .ant-alert-error, .ant-form-item-explain-error, "
        "[role='alert'], .ant-notification-notice-error"
    )
    login_left = False
    error_text = None
    try:
        page.wait_for_function(
            "url => window.location.href !== url",
            arg=page.url,
            timeout=8000,
        )
        login_left = True
    except Exception:
        # URL never changed -- check whether an error message showed up
        # in that same window instead.
        try:
            err_el = page.locator(error_selector).first
            if err_el.count() > 0:
                error_text = err_el.inner_text().strip()
        except Exception:
            pass

    print(f"  URL after submit: {page.url}")
    if login_left:
        print("  URL changed away from /login -- the request appears to have succeeded.")
    elif error_text:
        print(f"  Login form showed an error message: \"{error_text}\"")
        print("  This points to rejected credentials (wrong/expired password, "
              "account locked, etc.) rather than a selector/script problem.")
    else:
        print("  URL never changed and no error message element was found. "
              "Either the error renders via a selector not in the list above "
              "(check debug_login_after.png for the actual on-screen text), "
              "or the request is still pending/hanging.")

    page.screenshot(path="debug_login_after.png", full_page=True)

    try:
        page.wait_for_selector(config.logged_in_check_selector, timeout=10000)
        print("Logged in")
    except Exception:
        print("Logged-in indicator not found; continuing anyway")
        print(f"  Final URL: {page.url}")
        print(f"  If the URL above still looks like the login page, the submit "
              f"didn't go through. If it changed to a dashboard-like URL but this "
              f"still failed, config.logged_in_check_selector "
              f"('{config.logged_in_check_selector}') itself is probably stale "
              f"-- check debug_login_after.png for what's actually on screen.")

    # Optionally save auth state:
    # page.context.storage_state(path="auth_state.json")