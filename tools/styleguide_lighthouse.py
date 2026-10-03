"""Informational measurements at the design approval gate; no automatic tuning."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/styleguide-lighthouse'
OUT.mkdir(exist_ok=True)
environment = os.environ.copy()
environment['CHROME_PATH'] = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
parser = argparse.ArgumentParser()
parser.add_argument('--pages', nargs='+', choices=['home', 'styleguide'], default=['home', 'styleguide'])
args = parser.parse_args()
summary = OUT / 'summary.json'
rows = [row for row in json.loads(summary.read_text())['results'] if row['page'] not in args.pages] if summary.exists() else []
for name, url in [('home', 'http://127.0.0.1:8003/'), ('styleguide', 'http://127.0.0.1:8002/styleguide')]:
    if name not in args.pages:
        continue
    for profile in ['mobile', 'desktop']:
        target = OUT / f'{name}-{profile}.json'
        if target.exists():
            history = OUT / 'history'
            history.mkdir(exist_ok=True)
            shutil.copy2(target, history / f'{target.stem}-{target.stat().st_mtime_ns}.json')
        command = [r'C:\Program Files\nodejs\node.exe', 'node_modules/lighthouse/cli/index.js', url,
                   '--chrome-flags=--headless --no-sandbox', '--output=json', f'--output-path={target}', '--quiet']
        if profile == 'desktop':
            command.append('--preset=desktop')
        subprocess.run(command, cwd=ROOT, env=environment, check=True)
        data = json.loads(target.read_text(encoding='utf8'))
        audits = data['audits']
        requests = audits['network-requests']['details']['items']
        row = {'page': name, 'profile': profile, 'url': url, 'fetch_time': data['fetchTime'],
               'lighthouse_version': data['lighthouseVersion'],
               'scores': {key: round(value['score'] * 100) for key, value in data['categories'].items()},
               'lcp_ms': round(audits['largest-contentful-paint']['numericValue']),
               'cls': audits['cumulative-layout-shift']['numericValue'],
               'tbt_ms': round(audits['total-blocking-time']['numericValue']),
               'hero_video_requested': any('hero-drive' in item['url'] and '.mp4' in item['url'] for item in requests),
               'glb_or_three_requested': any('.glb' in item['url'] or '/three-' in item['url'] for item in requests)}
        rows.append(row)
        print(json.dumps(row), flush=True)
        (OUT / 'summary.json').write_text(json.dumps({
            'mode': 'Informational only; loopback Django/WhiteNoise, analytics disabled; styleguide intentionally noindex',
            'field_inp_measured': False, 'new_higgsfield_video_generated': False, 'results': rows,
        }, indent=2), encoding='utf8')
