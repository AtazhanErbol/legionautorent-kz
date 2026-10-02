"""Download original public images, validate pixels and produce responsive WebP."""
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit
import requests
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'media'
LIMIT = 10 * 1024 * 1024

def download(url):
    if urlsplit(url).hostname != 'legionautorent.kz' or urlsplit(url).scheme != 'https': raise ValueError('Only the audited legacy host is allowed.')
    token = hashlib.sha256(url.encode()).hexdigest()[:24]
    r = requests.get(url, timeout=30, stream=True, allow_redirects=False, headers={'User-Agent': 'LegionMigrationMedia/1.0'})
    r.raise_for_status()
    data = bytearray()
    for chunk in r.iter_content(65536):
        data.extend(chunk)
        if len(data) > LIMIT: raise ValueError('Image exceeds 10 MB')
    image = Image.open(io.BytesIO(data))
    fmt = image.format
    if fmt not in ('JPEG', 'PNG', 'WEBP', 'AVIF'): raise ValueError('Invalid image type')
    image.verify()
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
    suffix = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'AVIF': 'avif'}[fmt]
    original = f'cars/originals/{token}.{suffix}'
    (MEDIA / original).write_bytes(data)
    sizes = {}
    for width in [640, 1200]:
        clone = image.copy(); clone.thumbnail((width, 1000))
        target = f'cars/webp/{token}-{width}.webp'
        clone.save(MEDIA / target, 'WEBP', quality=82, method=6)
        sizes[width] = (target, clone.width, clone.height)
    result={'original': original, 'image': sizes[1200][0], 'small': sizes[640][0], 'width': sizes[1200][1], 'height': sizes[1200][2], 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    for size,field in [(640,'card_small'),(960,'card_image')]:
        width=min(size,image.width,int(image.height*1.55));height=round(width/1.55)
        card=ImageOps.fit(image,(width,height));target=f'cars/webp/{token}-card-{size}.webp'
        card.save(MEDIA/target,'WEBP',quality=76,method=6);result[field]=target
        if size==960:result['card_width'],result['card_height']=card.size
    return result

def run():
    data = json.loads((ROOT / 'migration/normalized.json').read_text(encoding='utf8'))
    manifest_file = ROOT / 'migration/media_manifest.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf8')) if manifest_file.exists() else {}
    for folder in ['cars/originals', 'cars/webp']: (MEDIA / folder).mkdir(parents=True, exist_ok=True)
    urls = sorted({i['url'] for car in data['cars'] for i in car['images']} | {'https://legionautorent.kz/img/car.png'})
    pending = [u for u in urls if u not in manifest or 'error' in manifest[u] or not (MEDIA / manifest[u]['original']).exists()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, u): u for u in pending}
        for i, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            try: manifest[url] = future.result()
            except Exception as exc: manifest[url] = {'error': str(exc)}
            if i % 20 == 0 or 'error' in manifest[url]: print(f'{i}/{len(pending)} downloaded; errors={sum("error" in x for x in manifest.values())}', flush=True)
            manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps({'unique_images': len(urls), 'downloaded': sum('error' not in x for x in manifest.values()), 'errors': {u: x['error'] for u, x in manifest.items() if 'error' in x}}))

if __name__ == '__main__': run()
