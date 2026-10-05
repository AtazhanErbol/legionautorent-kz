"""Create the 60-fps scroll derivative from the preserved approved raw film."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FF = ROOT / '.local/video-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
SOURCE = ROOT / 'review/mercedes-segment-01/raw.mp4'
WORK = ROOT / 'review/banner-reference-20261005'
WORK.mkdir(parents=True, exist_ok=True)
encoded = WORK / 'mercedes-motion-60-g8.mp4'
filters = 'trim=end_frame=140,scale=1440:-2,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1'
if not encoded.exists():
    subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-n', '-i', str(SOURCE),
                    '-vf', filters, '-c:v', 'libx264', '-crf', '20', '-preset', 'slow',
                    '-g', '8', '-keyint_min', '8', '-bf', '0', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-an', str(encoded)], check=True)
data = encoded.read_bytes()
digest = hashlib.sha256(data).hexdigest()
destination = ROOT / 'static/hero' / f'mercedes-segment-01-motion60-{digest[:12]}.mp4'
if not destination.exists():
    destination.write_bytes(data)
report = {
    'source': SOURCE.relative_to(ROOT).as_posix(),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'asset': destination.relative_to(ROOT).as_posix(),
    'sha256': digest, 'bytes': len(data), 'width': 1440, 'height': 810,
    'source_fps': 24, 'fps': 60, 'frames': 346, 'seconds': 346 / 60,
    'interpolation': filters, 'crf': 20, 'gop': 8, 'b_frames': 0,
    'audio': False, 'new_paid_generations': 0,
    'note': 'Motion interpolation synthesizes intermediate frames. Original footage and CMS source paths are retained.',
}
(ROOT / 'reports/banner_motion_asset.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
