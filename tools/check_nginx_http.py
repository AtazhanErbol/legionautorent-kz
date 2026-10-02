"""Exercise actual local Nginx MIME, compression negotiation and preserved assets."""
import gzip,json,os
from pathlib import Path
import brotli,requests

ROOT=Path(__file__).resolve().parents[1]
base=os.getenv('PREVIEW_URL','http://127.0.0.1:8004')
manifest=json.loads((ROOT/'static/build/.vite/manifest.json').read_text())
asset=manifest['frontend/main.js']['file']
expected=(ROOT/'static/build'/asset).read_bytes()
results=[]
for accept,encoding in [('br, gzip','br'),('gzip','gzip'),('identity',None),('br;q=0, gzip;q=0',None),('br;q=0, gzip;q=1','gzip')]:
    response=requests.get(base+'/static/build/'+asset,headers={'Accept-Encoding':accept},stream=True,timeout=20)
    wire=response.raw.read();actual=response.headers.get('Content-Encoding')
    assert response.status_code==200 and actual==encoding,(accept,response.status_code,actual)
    decoded=brotli.decompress(wire) if actual=='br' else gzip.decompress(wire) if actual=='gzip' else wire
    assert decoded==expected
    assert 'application/javascript' in response.headers['Content-Type'] and 'immutable' in response.headers['Cache-Control']
    results.append({'accept_encoding':accept,'served_encoding':actual,'bytes':len(wire),'pass':True})
for path,mime in [('/healthz/','application/json'),('/img/legionautorent.svg','image/svg+xml'),('/video/video-2.mp4?v=1.1','video/mp4')]:
    response=requests.get(base+path,timeout=20)
    assert response.status_code==200 and mime in response.headers['Content-Type'],(path,response.status_code,response.headers)
    results.append({'path':path,'status':200,'mime':response.headers['Content-Type'],'pass':True})
response=requests.get(base+'/img/car.png',timeout=20)
assert response.status_code==200 and len(response.history)==1 and response.history[0].status_code==301
results.append({'path':'/img/car.png','redirects':1,'status':200,'pass':True})
(ROOT/'reports/nginx_http.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results))
