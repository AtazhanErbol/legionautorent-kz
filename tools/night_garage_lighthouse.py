"""Informational audit of the approved design; never disables the active hero."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/final-lighthouse'
OUT.mkdir(exist_ok=True)
environment = os.environ.copy()
environment['CHROME_PATH'] = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
rows = []
for name, path in [('home', '/'), ('city', '/kostanay/'), ('car', '/car/lexus-lx-570-superior')]:
    for profile in ['mobile', 'desktop']:
        target = OUT / f'{name}-{profile}.json'
        command = [r'C:\Program Files\nodejs\node.exe', 'node_modules/lighthouse/cli/index.js',
                   'http://127.0.0.1:8003' + path, '--chrome-flags=--headless --no-sandbox',
                   '--output=json', f'--output-path={target}', '--quiet']
        if profile == 'desktop':
            command.append('--preset=desktop')
        cleanup_timeout = False
        if not target.exists():
            process = subprocess.Popen(command, cwd=ROOT, env=environment)
            try:
                code = process.wait(timeout=90)
                if code and not target.exists(): raise RuntimeError(f'Lighthouse exit {code}')
            except subprocess.TimeoutExpired:
                # Windows chrome-launcher can hang after writing a complete
                # LHR. Close only this invocation's process tree.
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else: process.kill()
                process.wait()
                cleanup_timeout = True
                if not target.exists(): raise RuntimeError('Lighthouse timed out without a report')
        data = json.loads(target.read_text(encoding='utf8'))
        audits = data['audits']
        requests = audits['network-requests']['details']['items']
        rows.append({
            'page': name, 'profile': profile, 'url': data['finalDisplayedUrl'],
            'fetch_time': data['fetchTime'], 'lighthouse_version': data['lighthouseVersion'],
            'browser_cleanup_timeout': cleanup_timeout,
            'scores': {key: round(value['score'] * 100) for key, value in data['categories'].items()},
            'lcp_ms': round(audits['largest-contentful-paint']['numericValue']),
            'cls': audits['cumulative-layout-shift']['numericValue'],
            'tbt_ms': round(audits['total-blocking-time']['numericValue']),
            'hero_video_requested': any('/hero/mercedes-' in item['url'] and '.mp4' in item['url'] for item in requests),
            'glb_or_three_requested': any('.glb' in item['url'] or '/three-' in item['url'] for item in requests),
        })
        print(json.dumps(rows[-1]), flush=True)
        (OUT / 'summary.json').write_text(json.dumps({
            'mode': 'Informational only; loopback Django/WhiteNoise production HTML, analytics disabled; approved Hailuo film enabled, normal mobile static gate',
            'field_inp_measured': False, 'new_higgsfield_video_generated': True, 'results': rows,
        }, indent=2), encoding='utf8')
