"""Compare actual displayed video frames, not just the browser's rAF cadence."""
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'codex/checkpoint-before-banner-motion-20261005'
old_controller = subprocess.check_output(['git', 'show', BASELINE + ':frontend/mercedes-preview.js'], cwd=ROOT).decode('utf-8')
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    for label in ['baseline', 'revised']:
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        if label == 'baseline':
            page.route('**/mercedes-preview-*.js', lambda route: route.fulfill(body=old_controller, content_type='application/javascript'))
            page.route('**/*motion60*.mp4', lambda route: route.fulfill(path=str(ROOT / 'static/hero/mercedes-segment-01-43d4cc20ca42.mp4'), content_type='video/mp4'))
        page.goto('http://127.0.0.1:8002/', wait_until='networkidle')
        page.wait_for_selector('[data-state=ready]')
        page.wait_for_timeout(600)
        trace = page.evaluate('''()=>new Promise(resolve=>{
            const video=document.querySelector('.mercedes-video'),hero=document.querySelector('[data-mercedes-preview]');
            const span=hero.offsetHeight-hero.firstElementChild.offsetHeight,shown=[],seeks=[],raf=[];
            let start=0,last=0,done=false,seekingAt=0;
            video.addEventListener('seeking',()=>seekingAt=performance.now());
            video.addEventListener('seeked',()=>seeks.push(performance.now()-seekingAt));
            function presented(now,meta){shown.push({at:now,time:meta.mediaTime});if(!done)video.requestVideoFrameCallback(presented)}
            video.requestVideoFrameCallback(presented);
            function tick(now){if(!start)start=now;if(last)raf.push(now-last);last=now;
                const t=Math.min(1,(now-start)/8000);
                scrollTo({top:span*(t<.5?t*2:(1-t)*2),behavior:'instant'});
                if(t<1)requestAnimationFrame(tick);else{done=true;resolve({shown,seeks,raf,width:video.videoWidth,height:video.videoHeight})}}
            requestAnimationFrame(tick);
        })''')
        unique = [value for i, value in enumerate(trace['shown']) if i == 0 or abs(value['time'] - trace['shown'][i - 1]['time']) > .001]
        gaps = [b['at'] - a['at'] for a, b in zip(unique, unique[1:])]
        moving = [b['at'] - a['at'] for previous, a, b in zip(unique, unique[1:], unique[2:])
                  if (b['time'] - a['time']) * (a['time'] - previous['time']) > 0]
        results.append({
            'label': label, 'size': [trace['width'], trace['height']],
            'changed_video_frames': len(unique), 'video_updates_per_second': round(len(unique) / 8, 2),
            'p95_video_gap_ms': round(sorted(gaps)[int(len(gaps) * .95)], 2),
            'longest_video_gap_ms_including_direction_reversal': round(max(gaps), 2),
            'longest_video_gap_ms_same_direction': round(max(moving), 2),
            'seek_count': len(trace['seeks']), 'mean_seek_ms': round(sum(trace['seeks']) / len(trace['seeks']), 2),
            'ui_average_fps': round(1000 / (sum(trace['raf']) / len(trace['raf'])), 2),
            'ui_longest_frame_ms': round(max(trace['raf']), 2),
        })
        page.close()
    browser.close()
report = {'scope': 'Same Chrome, 1440x900, eight seconds forward/reverse native scroll; no CPU throttle. Video frames via requestVideoFrameCallback; excludes identical mediaTime callbacks.',
          'reversal_note': 'A soft stop at direction reversal intentionally holds a frame; its full gap is also reported.', 'baseline_commit': BASELINE, 'runs': results}
(ROOT / 'reports/banner_presentation_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
