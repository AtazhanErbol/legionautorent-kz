"""A seamless forward/back loop of the already approved clean 60 fps film."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'static/hero/hero-scrub-smooth60-c86f40f74879.mp4'
FF = ROOT/'.local/video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
OUTPUT = ROOT/'review/showroom-smooth/hero-mobile-loop.mp4'
if not OUTPUT.exists():
    subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-n', '-i', str(SOURCE),
        '-filter_complex', '[0:v]split[f][r];[r]reverse,setpts=PTS-STARTPTS[rev];[f][rev]concat=n=2:v=1:a=0[v]',
        '-map', '[v]', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-threads', '2',
        '-g', '60', '-keyint_min', '60', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', str(OUTPUT)], check=True)
data = OUTPUT.read_bytes()
digest = hashlib.sha256(data).hexdigest()
target = ROOT/'static/hero'/f'hero-mobile-loop-{digest[:12]}.mp4'
if not target.exists(): target.write_bytes(data)
report = {'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'file': target.relative_to(ROOT).as_posix(), 'bytes': len(data), 'sha256': digest, 'duration_seconds': 15, 'fps': 60, 'resolution': [1280,720], 'audio': False, 'treatment': 'Approved film forward then reverse, no crop, upscale or generated imagery; CRF18, native inline playback.'}
(ROOT/'reports/mobile_loop_asset.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report))
