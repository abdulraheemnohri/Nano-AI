"""Optional, approval-gated browser automation. Install Playwright separately to enable it."""
import os
from urllib.parse import urlparse

def _allowed_url(url):
    if not isinstance(url,str) or len(url)>2048: raise ValueError("URL is required and limited to 2048 characters.")
    parsed=urlparse(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTP(S) URLs without embedded credentials are allowed.")
    allow={"localhost","127.0.0.1","::1"}
    allow.update(x.strip().lower() for x in os.getenv("NANO_BROWSER_ALLOWED_HOSTS","").split(",") if x.strip())
    if parsed.hostname.lower() not in allow:
        raise ValueError("Browser host is not allowlisted. Add its hostname to NANO_BROWSER_ALLOWED_HOSTS.")
    return url

def browser_action(action, url, selector=None, value=None, approved=False):
    if action not in {"inspect","click","fill"}: raise ValueError("Allowed actions: inspect, click, fill.")
    if action in {"click","fill"} and not approved: raise PermissionError("Explicit approval is required for click/fill actions.")
    if action=="fill" and (not isinstance(value,str) or len(value)>2000): raise ValueError("fill value is limited to 2000 characters.")
    if action in {"click","fill"} and (not isinstance(selector,str) or not selector.strip() or len(selector)>300): raise ValueError("A CSS selector is required.")
    target=_allowed_url(url)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Browser control requires optional Playwright: pip install playwright, then install its browser runtime.") from exc
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        try:
            def guard_route(route):
                try:
                    _allowed_url(route.request.url)
                    route.continue_()
                except ValueError:
                    route.abort()
            page.route("**/*", guard_route)
            page.goto(target,wait_until="domcontentloaded",timeout=15000)
            if action=="click": page.locator(selector).first.click(timeout=5000)
            elif action=="fill": page.locator(selector).first.fill(value,timeout=5000)
            return {"action":action,"url":page.url,"title":page.title(),"text":page.locator("body").inner_text(timeout=5000)[:10000]}
        finally:
            browser.close()
