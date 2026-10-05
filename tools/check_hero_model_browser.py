r"""Read-only Chromium checks/screenshots for the replacement hero model.

Run AFTER collectstatic and restarting the production preview at :8004.
Does not submit forms, contact anyone, change site data or modify frontend code.
Uses the existing desktop 3D / mobile poster behavior. This intentionally does
not run Lighthouse concurrently. Images and JSON go to dedicated model-audit
paths; historical visual-redesign and Lighthouse reports are never touched.

Usage: .venv\Scripts\python.exe tools/check_hero_model_browser.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("PREVIEW_URL", "http://127.0.0.1:8004"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/playwright/hero-model")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/hero_model_browser.json")
    parser.add_argument("--expected-model", type=Path, default=ROOT / "static/models/hero-compressed.glb")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {"time_utc": datetime.now(timezone.utc).isoformat(),
              "url": args.base_url.rstrip("/") + "/", "passed": False,
              "checks": {}, "desktop": {}, "mobile": {}, "scroll": [],
              "screenshots": [], "page_errors": [], "console_errors": [],
              "request_failures": [], "failures": []}

    def check(name, condition, detail=None):
        report["checks"][name] = bool(condition)
        if not condition:
            report["failures"].append({"check": name, "detail": detail})

    def screenshot(page, filename, **options):
        target = args.output_dir / filename
        page.screenshot(path=str(target), **options)
        report["screenshots"].append(str(target.resolve()))

    def attach_events(page, profile):
        page.on("pageerror", lambda error: report["page_errors"].append({"profile": profile, "message": str(error)}))
        page.on("console", lambda message: report["console_errors"].append({"profile": profile, "message": message.text}) if message.type == "error" else None)
        page.on("requestfailed", lambda request: report["request_failures"].append({"profile": profile, "url": request.url, "error": request.failure}))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome", headless=True,
                args=["--enable-webgl", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
            )
            desktop = browser.new_context(viewport={"width": 1440, "height": 1000},
                                          device_scale_factor=1, reduced_motion="no-preference")
            page = desktop.new_page()
            attach_events(page, "desktop")
            glb_responses = []
            page.on("response", lambda response: glb_responses.append(response) if ".glb" in response.url.split("?")[0] else None)
            response = page.goto(report["url"], wait_until="networkidle")
            check("desktop_http_200", response is not None and response.status == 200)
            page.wait_for_selector("[data-hero][data-state=ready]", timeout=60000)
            page.wait_for_timeout(1400)
            report["desktop"]["state"] = page.locator("[data-hero]").get_attribute("data-state")
            check("desktop_scene_ready", report["desktop"]["state"] == "ready")
            check("desktop_canvas_present", page.locator(".hero-canvas canvas").count() == 1)
            check("desktop_no_horizontal_overflow", not page.evaluate("document.documentElement.scrollWidth > innerWidth"))
            models = []
            for model_response in glb_responses:
                item = {"url": model_response.url, "status": model_response.status,
                        "content_type": model_response.headers.get("content-type"),
                        "content_encoding": model_response.headers.get("content-encoding"),
                        "content_length_header": model_response.headers.get("content-length")}
                try:
                    payload = model_response.body()
                    item.update({"decoded_response_bytes": len(payload), "sha256": sha256(payload)})
                except Exception as exc:
                    item["body_error"] = str(exc)
                models.append(item)
            report["desktop"]["models"] = models
            check("desktop_glb_requested", bool(models))
            if args.expected_model.exists():
                expected = args.expected_model.read_bytes()
                report["expected_model"] = {"path": str(args.expected_model.resolve()),
                                            "bytes": len(expected), "sha256": sha256(expected)}
                check("served_model_matches_disk", any(m.get("sha256") == sha256(expected) for m in models), models)
            else:
                check("expected_model_exists", False, str(args.expected_model))
            screenshot(page, "site-desktop.png")
            screenshot(page, "site-hero-closeup.png", clip={"x": 576, "y": 144, "width": 864, "height": 680})
            light = page.locator("[data-light-toggle]")
            check("headlights_initially_off", light.get_attribute("aria-pressed") == "false")
            before_lights = page.screenshot()
            light.click()
            page.wait_for_function("document.querySelector('[data-light-toggle]').getAttribute('aria-pressed') === 'true'")
            page.wait_for_timeout(650)
            check("headlights_toggle_on", light.get_attribute("aria-pressed") == "true")
            check("headlights_change_frame", before_lights != page.screenshot())
            screenshot(page, "site-lights.png")
            light.click()
            page.wait_for_function("document.querySelector('[data-light-toggle]').getAttribute('aria-pressed') === 'false'")
            check("headlights_toggle_off", light.get_attribute("aria-pressed") == "false")
            page.wait_for_timeout(650)
            hit = page.evaluate("document.elementFromPoint(1060,450)?.tagName")
            check("drag_target_is_canvas", hit == "CANVAS", hit)
            before_drag = page.screenshot()
            if hit == "CANVAS":
                page.mouse.move(1060, 450)
                page.mouse.down()
                page.mouse.move(1220, 470, steps=16)
                page.wait_for_timeout(180)
                after_drag = page.screenshot()
                screenshot(page, "site-drag.png")
                page.mouse.up()
                check("drag_changes_frame", before_drag != after_drag)
            # Reload restores the original camera/toggle, then samples actual
            # scrolling rather than relying on a misleading full-page capture.
            page.reload(wait_until="networkidle")
            page.wait_for_selector("[data-hero][data-state=ready]", timeout=60000)
            page.wait_for_timeout(900)
            for y in [0, 375, 740, 900, 1100, 1400]:
                page.evaluate("y => window.scrollTo({top:y, behavior:'instant'})", y)
                page.wait_for_timeout(950)
                sample = page.evaluate("""(() => {
                    const hero = document.querySelector('.hero').getBoundingClientRect();
                    const fleet = document.querySelector('#fleet').getBoundingClientRect();
                    const search = document.querySelector('.search-wrap').getBoundingClientRect();
                    const canvas = document.querySelector('.hero-canvas canvas');
                    return {requestedScroll: null, scroll: scrollY, viewport: innerHeight,
                        heroTop: hero.top, heroBottom: hero.bottom, fleetTop: fleet.top,
                        searchBottom: search.bottom,
                        visibleGap: Math.max(0, Math.min(fleet.top, innerHeight) - Math.max(hero.bottom, search.bottom, 0)),
                        solidHeader: document.querySelector('.site-header').classList.contains('is-scrolled'),
                        canvasPresent: !!canvas,
                        lightsPressed: document.querySelector('[data-light-toggle]').getAttribute('aria-pressed')};
                })()""")
                sample["requestedScroll"] = y
                report["scroll"].append(sample)
                check(f"scroll_{y}_no_blank_gap", sample["visibleGap"] < 2, sample)
                if y in (375, 740, 1100, 1400):
                    screenshot(page, f"site-scroll-{y}.png")
            check("catalog_enters_view_after_pin", report["scroll"][-1]["fleetTop"] < 1000,
                  report["scroll"][-1])
            card = page.locator(".car-card:not([hidden])").first
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            card_path = args.output_dir / "site-card-closeup.png"
            card.screenshot(path=str(card_path))
            report["screenshots"].append(str(card_path.resolve()))
            page.wait_for_load_state("networkidle")
            desktop.close()

            mobile = browser.new_context(viewport={"width": 390, "height": 844},
                                         device_scale_factor=1, is_mobile=True, has_touch=True,
                                         reduced_motion="no-preference")
            page = mobile.new_page()
            attach_events(page, "mobile")
            requests = []
            page.on("request", lambda request: requests.append(request.url))
            response = page.goto(report["url"], wait_until="networkidle")
            page.wait_for_timeout(1400)
            check("mobile_http_200", response is not None and response.status == 200)
            report["mobile"] = page.evaluate("""(() => {
                const poster = document.querySelector('.hero-poster');
                return {width: innerWidth, documentWidth: document.documentElement.scrollWidth,
                    state: document.querySelector('[data-hero]').dataset.state || 'poster',
                    canvasCount: document.querySelectorAll('.hero-canvas canvas').length,
                    posterComplete: poster.complete && poster.naturalWidth > 0,
                    posterSource: poster.currentSrc, posterOpacity: getComputedStyle(poster).opacity};
            })()""")
            report["mobile"]["model_requests"] = [url for url in requests if ".glb" in url.split("?")[0]]
            report["mobile"]["three_requests"] = [url for url in requests if "/three-" in url or "/hero-" in url and url.split("?")[0].endswith(".js")]
            check("mobile_no_glb", not report["mobile"]["model_requests"])
            check("mobile_no_scene_chunks", not report["mobile"]["three_requests"])
            check("mobile_no_canvas", report["mobile"]["canvasCount"] == 0)
            check("mobile_poster_loaded", report["mobile"]["posterComplete"] and float(report["mobile"]["posterOpacity"]) > 0)
            check("mobile_no_horizontal_overflow", report["mobile"]["documentWidth"] <= 390)
            screenshot(page, "site-mobile.png")
            page.locator(".car-card:not([hidden])").first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            check("mobile_catalog_no_horizontal_overflow", not page.evaluate("document.documentElement.scrollWidth > innerWidth"))
            screenshot(page, "site-mobile-catalog.png")
            page.wait_for_load_state("networkidle")
            mobile.close()
            browser.close()
        check("no_page_errors", not report["page_errors"], report["page_errors"])
        check("no_console_errors", not report["console_errors"], report["console_errors"])
        check("no_failed_requests", not report["request_failures"], report["request_failures"])
    except Exception as exc:
        report["failures"].append({"exception": type(exc).__name__, "message": str(exc)})
    report["passed"] = not report["failures"]
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(args.report.resolve()),
                      "checks": report["checks"], "failures": report["failures"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
