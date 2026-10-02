"""Mobile/desktop production-preview audits; never disables the live hero scene."""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/redesign-lighthouse';OUT.mkdir(exist_ok=True)
base=os.getenv('PREVIEW_URL','http://127.0.0.1:8004')
env=os.environ.copy();env['CHROME_PATH']=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
rows=[]
for profile in ['mobile','desktop']:
    for name,path in [('home','/'),('city','/kostanay/'),('car','/car/lexus-lx-570-superior'),('catalog','/cars/')]:
        target=OUT/f'{name}-{profile}.json'
        args=[r'C:\Program Files\nodejs\node.exe','node_modules/lighthouse/cli/index.js',base+path,'--chrome-flags=--headless --no-sandbox --enable-webgl --use-angle=swiftshader --enable-unsafe-swiftshader','--output=json',f'--output-path={target}','--quiet']
        if profile=='desktop':args+=['--preset=desktop']
        subprocess.run(args,cwd=ROOT,env=env,check=True)
        data=json.loads(target.read_text(encoding='utf8'));audits=data['audits']
        requests=audits['network-requests']['details']['items']
        row={'page':name,'profile':profile,'url':data['finalDisplayedUrl'],'lighthouse_version':data['lighthouseVersion'],'fetch_time':data['fetchTime'],'scores':{k:round(v['score']*100) for k,v in data['categories'].items()},'lcp_ms':round(audits['largest-contentful-paint']['numericValue']),'cls':audits['cumulative-layout-shift']['numericValue'],'tbt_ms':round(audits['total-blocking-time']['numericValue']),'hero_glb_requested':any('.glb' in r['url'] for r in requests),'hero_chunk_requested':any('/hero-' in r['url'] and r['url'].endswith('.js') for r in requests)}
        rows.append(row);print(json.dumps(row),flush=True)
        (OUT/'summary.json').write_text(json.dumps({'mode':'Local Nginx production HTML; analytics off; default mobile fallback, desktop 3D enabled; Chrome SwiftShader','field_inp_measured':False,'results':rows},indent=2),encoding='utf8')
