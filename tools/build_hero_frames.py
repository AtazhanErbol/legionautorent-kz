"""Build reproducible, progressively loaded WebP packs from a supplied video.

Requires ffmpeg with libwebp (set FFMPEG or pass --ffmpeg). No generation,
interpolation, cropping, audio, or modification of the supplied car footage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--ffmpeg', default=os.getenv('FFMPEG', 'ffmpeg'))
    parser.add_argument('--output', type=Path, default=ROOT / 'static/hero')
    parser.add_argument('--url-prefix', default='/static/hero')
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(*arguments, capture=False):
        command = [str(args.ffmpeg), '-hide_banner', *map(str, arguments)]
        commands.append(command)
        return subprocess.run(command, check=True, capture_output=capture, text=capture)

    probe = run('-i', source, '-map', '0:v:0', '-an', '-f', 'null', '-', capture=True)
    count = int(re.findall(r'frame=\s*(\d+)', probe.stderr)[-1])
    fps = float(re.search(r'(\d+(?:\.\d+)?) fps', probe.stderr).group(1))
    width, height = map(int, re.search(r'(\d{3,5})x(\d{3,5})', probe.stderr).groups())
    if width / height != 16 / 9 or count < 2:
        raise SystemExit('Expected a complete 16:9 orbit with at least two frames.')
    master = output / 'hero-60fps.mp4'
    if source != master:
        run('-loglevel', 'error', '-y', '-i', source, '-map', '0:v:0',
            '-c:v', 'copy', '-an', '-movflags', '+faststart', master)
    digest = hashlib.sha256(master.read_bytes()).hexdigest()
    pack_root = output / ('frames-' + digest[:12])
    pack_root.mkdir(exist_ok=True)
    url = args.url_prefix.rstrip('/')
    result = {'version': 1, 'master': url + '/' + master.name,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'master_sha256': digest, 'master_bytes': master.stat().st_size,
              'source_width': width, 'source_height': height, 'source_fps': fps,
              'count': count, 'fps': fps, 'duration': count / fps,
              'last_time': (count - 1) / fps, 'audio': False, 'pack_size': 8}

    # Each pack is a concatenation of [little-endian uint32 length, WebP bytes].
    # Keep full source timing, including the exact first and last frame.
    with tempfile.TemporaryDirectory(prefix='legion-hero-') as work:
        work = Path(work)
        for name, target_width, quality in [('desktop', min(1280, width), 82),
                                            ('mobile', min(768, width), 78)]:
            directory = work / name
            directory.mkdir()
            run('-loglevel', 'error', '-y', '-i', master, '-map', '0:v:0', '-an',
                '-vf', f'scale={target_width}:-2:flags=lanczos,setsar=1',
                '-fps_mode', 'passthrough', '-c:v', 'libwebp', '-quality', quality,
                '-compression_level', '5', '-start_number', '0', directory / '%04d.webp')
            frames = sorted(directory.glob('*.webp'))
            assert len(frames) == count, (len(frames), count)
            packs = []
            for start in range(0, count, result['pack_size']):
                filename = f'{name}-{start // result["pack_size"]:02d}.pack'
                payload = b''.join(struct.pack('<I', frame.stat().st_size) + frame.read_bytes()
                                   for frame in frames[start:start + result['pack_size']])
                (pack_root / filename).write_bytes(payload)
                packs.append({'url': f'{url}/{pack_root.name}/{filename}',
                              'start': start, 'count': min(result['pack_size'], count - start),
                              'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
            poster = output / f'hero-poster-60fps-{name}.webp'
            shutil.copyfile(frames[0], poster)
            result[name] = {'width': target_width, 'height': target_width * 9 // 16,
                            'count': count, 'quality': quality, 'packs': packs,
                            'bytes': sum(pack['bytes'] for pack in packs),
                            'poster': f'{url}/{poster.name}', 'poster_bytes': poster.stat().st_size}
            if name == 'desktop':
                ending = output / 'hero-ending-60fps.webp'
                shutil.copyfile(frames[-1], ending)
                result['ending'] = f'{url}/{ending.name}'
                result['ending_bytes'] = ending.stat().st_size

    (output / 'sequence.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    report = ROOT / 'reports/hero_frames_asset.json'
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps({**result, 'commands': commands}, indent=2), encoding='utf8')
    print(json.dumps({key: result[key] for key in ('count', 'fps', 'duration', 'master_bytes')}))
    for name in ('mobile', 'desktop'):
        print(name, result[name]['bytes'], 'bytes;', len(result[name]['packs']), 'packs')


if __name__ == '__main__':
    main()
