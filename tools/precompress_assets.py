"""Precompress Vite assets once at build time. No originals or old assets are deleted."""
import argparse,json,gzip
from pathlib import Path
import zopfli.gzip
import brotli
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--root',default='static/build');args=parser.parse_args()
folder=ROOT/args.root
manifest=json.loads((ROOT/'static/build/.vite/manifest.json').read_text(encoding='utf8'))
sizes={}
for css in {file for item in manifest.values() for file in item.get('css',[])}:
    path=folder/css;data=path.read_bytes();Path(str(path)+'.gz').write_bytes(zopfli.gzip.compress(data,numiterations=10));Path(str(path)+'.br').write_bytes(brotli.compress(data,quality=11))
for item in manifest.values():
    if not item['file'].endswith(('.js','.css')):continue
    # --root staticfiles/build runs AFTER collectstatic to preserve the tight gzip budget.
    path=folder/item['file'];data=path.read_bytes();compressed=zopfli.gzip.compress(data,numiterations=10)
    Path(str(path)+'.gz').write_bytes(compressed);Path(str(path)+'.br').write_bytes(brotli.compress(data,quality=11))
    sizes[item.get('name',item['file'])]=len(compressed)
total=sum(sizes.get(name,0) for name in ['three','hero','meshopt_decoder.module'])
report={'main_gzip_bytes':sizes.get('main'),'three_scene_decoder_gzip_bytes':total,'three_scene_budget_bytes':150000,'motion_gzip_bytes':sizes.get('motion'),'model_bytes':(ROOT/'static/models/hero-compressed.glb').stat().st_size,'poster_bytes':(ROOT/'static/img/hero-poster.webp').stat().st_size,'gzip_sizes':sizes}
(ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/asset_budget.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
if total>=150000:raise SystemExit('Three/scene/decoder gzip budget exceeded')
