"""Encode the owner's first reviewed segment; preserve raw and old site assets."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'review/mercedes-segment-01/raw.mp4'
FF = ROOT / '.local/video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
WORK = ROOT / 'review/mercedes-segment-01/web'
DEST = ROOT / 'static/hero'
WORK.mkdir(parents=True, exist_ok=True)
DEST.mkdir(parents=True, exist_ok=True)
def encode(args, name):
    path = WORK / name
    subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-y', *args, str(path)], check=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    target = DEST / f'{path.stem}-{digest}{path.suffix}'
    target.write_bytes(path.read_bytes())
    return {'path': target.relative_to(ROOT / 'static').as_posix(), 'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
assets = {
    'video': encode(['-i',str(RAW),'-frames:v','140','-c:v','libx264','-crf','18','-preset','slow','-g','8','-keyint_min','8','-pix_fmt','yuv420p','-movflags','+faststart','-an'], 'mercedes-segment-01.mp4'),
    'poster': encode(['-i',str(RAW),'-frames:v','1','-c:v','libwebp','-quality','92'], 'mercedes-front.webp'),
    'mobile': encode(['-i',str(RAW),'-frames:v','1','-vf','scale=960:-2','-c:v','libwebp','-quality','92'], 'mercedes-front-mobile.webp'),
    'ending': encode(['-i',str(RAW),'-vf','select=eq(n\\,139)','-frames:v','1','-c:v','libwebp','-quality','92'], 'mercedes-ending.webp'),
}
report = {'purpose':'Local on-site preview for owner approval, not final approval', 'source_job':'16341aed-e0d0-4e6b-8f1d-d02d60cc3322','frames':140,'fps':24,'width':1918,'height':1080,'seconds':140/24,'audio':False,'assets':assets}
(ROOT / 'reports/mercedes_preview_assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
