"""Wait for page load without treating an open media stream as unfinished UI."""
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def open_loaded_page(page, url, report):
    pending = set()
    started = lambda request: pending.add(request.url)
    finished = lambda request: pending.discard(request.url)
    page.on('request', started)
    page.on('requestfinished', finished)
    page.on('requestfailed', finished)
    try:
        response = page.goto(url, wait_until='load')
        try:
            page.wait_for_load_state('networkidle', timeout=5000)
        except PlaywrightTimeoutError:
            # Callers still assert decoded-video readiness, expected state and
            # complete layout. Preserve stalled request evidence in the report.
            report.setdefault('network_idle_fallbacks', []).append({
                'url':url, 'pending':sorted(pending),
                'ready_state':page.evaluate('document.readyState'),
            })
        return response
    finally:
        page.remove_listener('request', started)
        page.remove_listener('requestfinished', finished)
        page.remove_listener('requestfailed', finished)
