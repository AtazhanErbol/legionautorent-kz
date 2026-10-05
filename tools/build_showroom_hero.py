"""Prepare the supplied showroom clip once; never regenerate or upscale footage."""
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FF = ROOT / '.local/video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
SOURCE = ROOT / 'design_refs/hero/hero-source.mp4'
WORK = ROOT / 'review/showroom-source'
ASSETS = ROOT / 'static/hero'
WORK.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

def publish(path, name):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    target = ASSETS / f'{name}-{digest[:12]}{path.suffix}'
    if not target.exists():
        target.write_bytes(data)
    return {'path': '/static/' + target.relative_to(ROOT/'static').as_posix(),
            'bytes': len(data), 'sha256': digest}

# End before the increasingly garbled rear lettering/plate in the supplied tail.
encoded = WORK / 'hero-scrub-crf20-g8.mp4'
command = [str(FF), '-hide_banner', '-loglevel', 'error', '-n', '-i', str(SOURCE),
           '-t', '7.5', '-c:v', 'libx264', '-crf', '20', '-preset', 'slow',
           '-g', '8', '-keyint_min', '8', '-bf', '0', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', '-an', str(encoded)]
if not encoded.exists():
    subprocess.run(command, check=True)
assets = {'video': publish(encoded, 'hero-scrub')}
for key, timestamp in [('poster', 0), ('mobile', 3.5), ('ending', 179/24)]:
    png = WORK / f'asset-{key}.png'
    subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(timestamp),
                    '-i', str(encoded), '-frames:v', '1', '-update', '1', str(png)], check=True)
    webp = WORK / f'asset-{key}.webp'
    Image.open(png).save(webp, 'WEBP', quality=94, method=6)
    assets[key] = {**publish(webp, {'poster':'hero-poster','mobile':'hero-static','ending':'hero-ending'}[key]), 'time': timestamp}

report = {'source': SOURCE.relative_to(ROOT).as_posix(), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'source_bytes': SOURCE.stat().st_size, 'source_duration': 10, 'width':1280, 'height':720,
          'fps':24, 'frames':180, 'duration':7.5, 'last_frame_time':179/24, 'crf':20,
          'gop':8, 'b_frames':0, 'audio':False, 'upscaled':False, 'interpolated':False,
          'paid_generations':0, 'assets':assets, 'command':command,
          'source_has_natural_rest':False, 'trim_reason':'Garbled rear lettering/plate becomes prominent in the tail; keep the rear three-quarter frame before that tail.'}
assert assets['video']['bytes'] < 10_000_000
(ROOT/'reports/showroom_assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
