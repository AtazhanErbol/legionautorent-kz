"""Audits with an explicitly owned browser (avoids Windows CLI cleanup hangs)."""
import json
import subprocess
import socket
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/os.environ.get('LEGION_AUDIT_OUTPUT','reports/final-cms-20261005');OUT.mkdir(exist_ok=True)
rows=[]
with sync_playwright() as p:
    for profile in ('mobile','desktop'):
        for name,path in [('home','/'),('city','/kostanay/'),('car','/car/lexus-lx-570-superior'),('catalog','/cars/')]:
            target=OUT/f'{name}-{profile}.json'
            if not target.exists():
                with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
                browser=p.chromium.launch(channel='chrome',headless=True,args=[f'--remote-debugging-port={port}'])
                try:
                    args=[r'C:\Program Files\nodejs\node.exe','node_modules/lighthouse/cli/index.js','http://127.0.0.1:8003'+path,f'--port={port}','--output=json',f'--output-path={target}','--quiet']
                    if profile=='desktop':args.append('--preset=desktop')
                    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=120)
                    if result.returncode:raise RuntimeError(result.stderr)
                finally:browser.close()
            data=json.loads(target.read_text(encoding='utf8'));assert not data.get('runtimeError'),data.get('runtimeError')
            audits=data['audits'];requests=audits['network-requests']['details']['items']
            row={'page':name,'profile':profile,'url':data['finalDisplayedUrl'],'lighthouse_version':data['lighthouseVersion'],'fetch_time':data['fetchTime'],'scores':{k:round(v['score']*100) for k,v in data['categories'].items()},'lcp_ms':round(audits['largest-contentful-paint']['numericValue']),'cls':audits['cumulative-layout-shift']['numericValue'],'tbt_ms':round(audits['total-blocking-time']['numericValue']),'hero_video_requested':any('hero-scrub-' in r['url'] and '.mp4' in r['url'] for r in requests),'hero_mobile_loop_requested':any('hero-mobile-loop-' in r['url'] for r in requests)}
            rows.append(row);print(json.dumps(row),flush=True)
            (OUT/'summary.json').write_text(json.dumps({'mode':'Production rendering on local :8003; analytics off; desktop scrub enabled; mobile motion starts on first interaction and is tested separately. Default Lighthouse profiles, explicitly managed Chrome.','field_inp_measured':False,'results':rows},indent=2),encoding='utf8')
