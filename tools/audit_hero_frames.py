"""Lighthouse home audits with the canvas animation enabled on both profiles."""
import json
from pathlib import Path
import socket
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/hero-60fps-lighthouse'
OUT.mkdir(exist_ok=True)
rows=[]
with sync_playwright() as p:
    for profile in ('mobile','desktop'):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        browser=p.chromium.launch(channel='chrome',headless=True,args=[f'--remote-debugging-port={port}'])
        try:
            target=OUT/f'home-{profile}.json'
            command=[r'C:\Program Files\nodejs\node.exe','node_modules/lighthouse/cli/index.js','http://127.0.0.1:8003/',f'--port={port}','--output=json',f'--output-path={target}','--quiet']
            if profile=='desktop':command.append('--preset=desktop')
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=150)
            if result.returncode:raise RuntimeError(result.stderr)
            data=json.loads(target.read_text(encoding='utf8'))
            assert not data.get('runtimeError'),data.get('runtimeError')
            audits=data['audits']
            row={'profile':profile,'lighthouse_version':data['lighthouseVersion'],
                 'scores':{k:round(v['score']*100) for k,v in data['categories'].items()},
                 'lcp_ms':round(audits['largest-contentful-paint']['numericValue']),
                 'cls':audits['cumulative-layout-shift']['numericValue'],
                 'tbt_ms':round(audits['total-blocking-time']['numericValue']),
                 'pack_requests':sum('.pack' in r['url'] for r in audits['network-requests']['details']['items']),
                 'mp4_requested':any('.mp4' in r['url'] for r in audits['network-requests']['details']['items'])}
            assert row['pack_requests']>0 and not row['mp4_requested']
            rows.append(row);print(json.dumps(row),flush=True)
        finally:browser.close()
(OUT/'summary.json').write_text(json.dumps({'field_inp_measured':False,'animation_enabled':True,'results':rows},indent=2),encoding='utf8')
