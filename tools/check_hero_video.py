r"""Read-only real-browser audit of the reference-film scroll hero.

Run after the production preview on :8004 has been refreshed. All fixtures are
Playwright routes/browser state; no database settings or source assets change.
The clip must already exist at /static/video/hero-reference.mp4.
Usage: .venv\Scripts\python.exe tools/check_hero_video.py
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIDEO_PATH = "/static/video/hero-reference.mp4"
READY = "[data-hero][data-state=video-ready]"
PIXELS = """() => {
    const v=document.querySelector('.hero-video'), c=document.createElement('canvas');
    c.width=160;c.height=90;const ctx=c.getContext('2d',{willReadFrequently:true});
    ctx.drawImage(v,0,0,c.width,c.height);const pixels=ctx.getImageData(0,0,c.width,c.height).data;
    let hash=2166136261,sum=0,squared=0;
    for(let i=0;i<pixels.length;i+=4){
        const l=(pixels[i]+pixels[i+1]+pixels[i+2])/3;sum+=l;squared+=l*l;
        for(let j=0;j<3;j++){hash^=pixels[i+j];hash=Math.imul(hash,16777619);}
    }
    const mean=sum/(160*90);
    return {time:v.currentTime,duration:v.duration,seeking:v.seeking,paused:v.paused,
        readyState:v.readyState,videoWidth:v.videoWidth,videoHeight:v.videoHeight,
        pixelHash:(hash>>>0).toString(16),meanLuminance:mean,
        luminanceDeviation:Math.sqrt(squared/(160*90)-mean*mean),png:c.toDataURL('image/png')};
}"""
GAP = """() => {
    const h=document.querySelector('.hero').getBoundingClientRect(),
          f=document.querySelector('#fleet').getBoundingClientRect(),
          s=document.querySelector('.search-wrap').getBoundingClientRect();
    return {scroll:scrollY,width:innerWidth,height:innerHeight,heroBottom:h.bottom,
        fleetTop:f.top,searchBottom:s.bottom,
        visibleGap:Math.max(0,Math.min(f.top,innerHeight)-Math.max(h.bottom,s.bottom,0)),
        overflow:document.documentElement.scrollWidth>innerWidth};
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("PREVIEW_URL", "http://127.0.0.1:8004"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output/playwright/hero-video")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/hero_video_browser.json")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    report = {"utc": datetime.now(timezone.utc).isoformat(), "base_url": base,
              "passed": False, "checks": {}, "failures": [], "frames": [],
              "scroll": [], "diagnostics": [], "screenshots": [], "cases": [], "posters": {}}

    def check(name, passed, detail=None):
        report["checks"][name] = bool(passed)
        if not passed:
            report["failures"].append({"check": name, "detail": detail})

    def shot(page, name):
        target = args.output_dir / name
        page.screenshot(path=str(target))
        report["screenshots"].append(str(target.resolve()))

    def frame(page, name):
        data = page.evaluate(PIXELS)
        target = args.output_dir / f"frame-{name}.png"
        target.write_bytes(base64.b64decode(data.pop("png").split(",", 1)[1]))
        data.update({"name": name, "file": str(target.resolve())})
        report["frames"].append(data)
        check(f"frame_{name}_decoded", data["readyState"] >= 2 and data["videoWidth"] > 0
              and data["luminanceDeviation"] > 2 and not data["seeking"], data)
        return data

    def no_3d(requests):
        return not any(".glb" in url or "/three-" in url or re.search(r"/hero-(?!video-)[^/]+\.js", url)
                       for url in requests)

    def pin_geometry(page):
        return page.evaluate("""() => {
            const h=document.querySelector('[data-hero]'), p=h.parentElement,
                r=p.getBoundingClientRect();
            return {start:r.top+scrollY,span:p.offsetHeight-h.offsetHeight,
                pinned:p.classList.contains('pin-spacer'),heroHeight:h.offsetHeight};
        }""")

    def scrub(page, progress, name, geometry):
        page.evaluate("y => scrollTo({top:y,behavior:'instant'})", geometry["start"] + geometry["span"] * progress)
        page.wait_for_function("""p => {
            const v=document.querySelector('.hero-video');
            return v && !v.seeking && v.readyState>=2 &&
                Math.abs(v.currentTime-Math.min(v.duration-1/30,p*v.duration))<.09;
        }""", arg=progress, timeout=20000)
        # currentTime is observable before a new frame reaches the compositor.
        page.wait_for_timeout(380)
        data = frame(page, name)
        sample = page.evaluate(GAP)
        sample["rearShadeOpacity"] = page.locator(".hero-stage").evaluate("element=>Number(getComputedStyle(element,'::after').opacity)")
        sample["name"] = name
        report["scroll"].append(sample)
        check(f"gap_{name}", sample["visibleGap"] < 2 and not sample["overflow"], sample)
        if progress == 1:
            check(f"rear_text_shade_{name}", sample["rearShadeOpacity"] > .95, sample["rearShadeOpacity"])
        shot(page, f"site-{name}.png")
        return data

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)

            def new_case(name, width=1440, height=1000, reduced=False, save_data=False, force_both=False, gate_idle=False):
                context = browser.new_context(viewport={"width": width, "height": height},
                                              device_scale_factor=1, is_mobile=width < 768,
                                              has_touch=width < 768,
                                              reduced_motion="reduce" if reduced else "no-preference")
                context.add_init_script("""window.__heroTest={plays:0};
                    document.addEventListener('play',e=>{if(e.target.classList?.contains('hero-video'))window.__heroTest.plays++},true);""")
                if save_data:
                    context.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true}})")
                if gate_idle:
                    context.add_init_script("""window.__heroIdle=[];
                        window.requestIdleCallback=callback=>{window.__heroIdle.push(callback);return window.__heroIdle.length};
                        window.cancelIdleCallback=id=>{window.__heroIdle[id-1]=null};""")
                if force_both:
                    def html_fixture(route):
                        response = route.fetch()
                        html = re.sub(r'data-enabled="[^"]*"', 'data-enabled="true"', response.text(), count=1)
                        html = re.sub(r'data-video="[^"]*"', f'data-video="{VIDEO_PATH}"', html, count=1)
                        route.fulfill(response=response, body=html)
                    context.route(base + "/", html_fixture)
                page = context.new_page()
                requests, errors = [], []
                page.on("request", lambda request: requests.append(request.url))
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: report["diagnostics"].append({"case": name, "type": message.type, "text": message.text})
                        if message.type in ("warning", "error") else None)
                report["cases"].append(name)
                return context, page, requests, errors

            # Deliberately hold requestIdleCallback to demonstrate that media is
            # not fetched merely because SSR markup contains its path.
            context, page, requests, errors = new_case("desktop", gate_idle=True)
            response = page.goto(base + "/", wait_until="networkidle")
            check("home_200", response.status == 200)
            check("configured_video", page.locator("[data-hero]").get_attribute("data-video") == VIDEO_PATH)
            desktop_poster = page.locator("img.hero-poster").evaluate("p=>p.currentSrc")
            report["posters"]["desktop"] = desktop_poster
            check("desktop_poster_is_expected", bool(re.search(r"/static/img/hero-video-poster(?:\.[0-9a-f]+)?\.webp$", desktop_poster)), desktop_poster)
            check("desktop_does_not_request_mobile_poster", not any("hero-video-mobile" in url for url in requests))
            page.wait_for_timeout(300)
            check("video_deferred_until_idle", not any(VIDEO_PATH in url for url in requests))
            check("no_3d_before_video", no_3d(requests))
            page.evaluate("window.__heroIdle.splice(0).forEach(callback=>callback?.({didTimeout:false,timeRemaining:()=>50}))")
            page.wait_for_selector(READY, timeout=30000)
            duration = page.locator(".hero-video").evaluate("v=>v.duration")
            check("clip_duration_approximately_9_seconds", 8 <= duration <= 9.2, duration)
            geometry = pin_geometry(page)
            check("one_hero_pin", geometry["pinned"] and page.locator(".pin-spacer").count() == 1, geometry)
            check("positive_scrub_span", geometry["span"] > 0, geometry)
            check("desktop_no_3d_requests", no_3d(requests), requests)
            controls = page.locator(".hero-video").evaluate("v=>({paused:v.paused,autoplay:v.autoplay,loop:v.loop,muted:v.muted,playsInline:v.playsInline})")
            check("video_is_paused_not_autoplay_loop", controls["paused"] and not controls["autoplay"] and not controls["loop"] and controls["muted"] and controls["playsInline"], controls)
            frames = [scrub(page, fraction, name, geometry) for fraction, name in
                      [(0, "front"), (.5, "profile"), (1, "rear"), (.5, "reverse-profile"), (0, "reverse-front")]]
            check("three_distinct_decoded_views", len({f["pixelHash"] for f in frames[:3]}) == 3)
            check("reverse_restores_profile_frame", frames[1]["pixelHash"] == frames[3]["pixelHash"])
            check("reverse_restores_front_frame", frames[0]["pixelHash"] == frames[4]["pixelHash"])
            still_time = page.locator(".hero-video").evaluate("v=>v.currentTime")
            page.wait_for_timeout(600)
            check("no_playback_while_scroll_stopped", abs(page.locator(".hero-video").evaluate("v=>v.currentTime") - still_time) < .01)
            check("play_was_never_called", page.evaluate("window.__heroTest.plays") == 0)
            # Multiple desired positions in rapid succession must settle on the
            # last one, regardless of ongoing decode/seek completion ordering.
            for fraction in [.95, .15, .8, .3, .6, .22]:
                page.evaluate("y=>scrollTo({top:y,behavior:'instant'})", geometry["start"] + fraction * geometry["span"])
                page.wait_for_timeout(18)
            scrub(page, .22, "rapid-final", geometry)
            for distance in [geometry["span"] - 4, geometry["span"] + 100,
                             geometry["span"] + 500, geometry["span"] + 900]:
                page.evaluate("y=>scrollTo({top:y,behavior:'instant'})", geometry["start"] + distance)
                page.wait_for_timeout(450)
                sample = page.evaluate(GAP); report["scroll"].append(sample)
                check(f"desktop_pin_exit_{round(distance)}", sample["visibleGap"] < 2 and not sample["overflow"], sample)
            shot(page, "site-catalog-after-pin.png")
            check("desktop_no_page_errors", not errors, errors)
            context.close()

            for width, height in [(768, 1024), (1024, 900)]:
                context, page, requests, errors = new_case(f"responsive-{width}", width, height)
                page.goto(base + "/", wait_until="networkidle"); page.wait_for_selector(READY, timeout=30000)
                geometry = pin_geometry(page)
                for progress in [0, .5, 1]:
                    scrub(page, progress, f"{width}-{int(progress*100)}", geometry)
                check(f"responsive_{width}_no_3d", no_3d(requests))
                check(f"responsive_{width}_no_page_errors", not errors, errors)
                context.close()

            for name, options in [("mobile", {"width": 390, "height": 844}),
                                  ("small-mobile", {"width": 320, "height": 740}),
                                  ("reduced-motion", {"reduced": True}),
                                  ("save-data", {"save_data": True})]:
                context, page, requests, errors = new_case(name, **options)
                page.goto(base + "/", wait_until="networkidle"); page.wait_for_timeout(1500)
                poster = page.locator("img.hero-poster").evaluate("p=>({complete:p.complete,width:p.naturalWidth,opacity:getComputedStyle(p).opacity,currentSrc:p.currentSrc})")
                report["posters"][name] = poster
                if name in ("mobile", "small-mobile"):
                    check(f"{name}_uses_mobile_poster", bool(re.search(r"/static/img/hero-video-mobile(?:\.[0-9a-f]+)?\.webp$", poster["currentSrc"])), poster)
                    check(f"{name}_does_not_download_desktop_poster", not any("hero-video-poster" in url for url in requests), requests)
                else:
                    check(f"{name}_uses_desktop_poster", bool(re.search(r"/static/img/hero-video-poster(?:\.[0-9a-f]+)?\.webp$", poster["currentSrc"])), poster)
                check(f"{name}_poster_visible", poster["complete"] and poster["width"] > 0 and float(poster["opacity"]) > 0, poster)
                check(f"{name}_no_video_request", not any(VIDEO_PATH in url for url in requests))
                check(f"{name}_no_3d", no_3d(requests))
                check(f"{name}_no_pin", page.locator(".pin-spacer").count() == 0)
                check(f"{name}_no_overflow", not page.evaluate("document.documentElement.scrollWidth>innerWidth"))
                shot(page, f"site-{name}.png")
                page.locator("#fleet").scroll_into_view_if_needed()
                check(f"{name}_catalog_no_overflow", not page.evaluate("document.documentElement.scrollWidth>innerWidth"))
                check(f"{name}_no_page_errors", not errors, errors)
                context.close()

            context, page, requests, errors = new_case("video-priority", force_both=True)
            page.goto(base + "/", wait_until="networkidle"); page.wait_for_selector(READY, timeout=30000)
            check("video_wins_when_3d_enabled", no_3d(requests) and page.locator(".hero-video").count() == 1, requests)
            check("priority_no_page_errors", not errors, errors)
            context.close()

            context, page, requests, errors = new_case("404-fallback", force_both=True)
            context.route("**" + VIDEO_PATH, lambda route: route.fulfill(status=404, body="Missing test video", content_type="text/plain"))
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_selector("[data-hero][data-state=fallback]", timeout=20000)
            check("404_removes_pin", page.locator(".pin-spacer").count() == 0)
            check("404_removes_video", page.locator(".hero-video").count() == 0)
            check("404_restores_poster", float(page.locator("img.hero-poster").evaluate("p=>getComputedStyle(p).opacity")) > 0)
            check("404_does_not_revert_to_3d", no_3d(requests), requests)
            check("404_restores_heading", page.locator(".hero-copy").is_visible())
            shot(page, "site-404-fallback.png")
            check("404_no_page_errors", not errors, errors)
            context.close()

            context, page, requests, errors = new_case("live-reduced-motion")
            page.goto(base + "/", wait_until="networkidle"); page.wait_for_selector(READY, timeout=30000)
            page.emulate_media(reduced_motion="reduce")
            page.wait_for_function("!document.querySelector('.hero-video') && !document.querySelector('.pin-spacer')", timeout=10000)
            check("live_reduce_unpins", page.locator(".pin-spacer").count() == 0)
            check("live_reduce_removes_video", page.locator(".hero-video").count() == 0)
            check("live_reduce_restores_copy", page.locator(".hero-copy").is_visible())
            context.close()

            context, page, requests, errors = new_case("resize-lifecycle")
            page.goto(base + "/", wait_until="networkidle"); page.wait_for_selector(READY, timeout=30000)
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_function("!document.querySelector('.hero-video') && !document.querySelector('.pin-spacer')", timeout=10000)
            check("resize_to_mobile_unpins", page.locator(".pin-spacer").count() == 0)
            check("resize_to_mobile_restores_poster", float(page.locator("img.hero-poster").evaluate("p=>getComputedStyle(p).opacity")) > 0)
            check("resize_to_mobile_no_overflow", not page.evaluate("document.documentElement.scrollWidth>innerWidth"))
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.wait_for_selector(READY, timeout=30000)
            check("resize_back_one_video_one_pin", page.locator(".hero-video").count() == 1 and page.locator(".pin-spacer").count() == 1)
            check("resize_no_page_errors", not errors, errors)
            context.close()

            context, page, requests, errors = new_case("pagehide")
            page.goto(base + "/", wait_until="networkidle"); page.wait_for_selector(READY, timeout=30000)
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
            page.wait_for_timeout(200)
            check("pagehide_cleans_video", page.locator(".hero-video").count() == 0)
            check("pagehide_cleans_pin", page.locator(".pin-spacer").count() == 0)
            check("pagehide_restores_poster", float(page.locator("img.hero-poster").evaluate("p=>getComputedStyle(p).opacity")) > 0)
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
            page.wait_for_selector(READY, timeout=30000)
            check("pageshow_restores_one_video_one_pin", page.locator(".hero-video").count() == 1 and page.locator(".pin-spacer").count() == 1)
            check("pagehide_no_page_errors", not errors, errors)
            context.close()
            browser.close()
    except Exception as exc:
        report["failures"].append({"exception": type(exc).__name__, "message": str(exc)})
    report["passed"] = not report["failures"]
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(args.report.resolve()),
                      "checks": len(report["checks"]), "failures": report["failures"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
