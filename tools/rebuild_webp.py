"""Rebuild responsive formats from preserved originals, retaining PNG transparency."""
import json
from pathlib import Path
from PIL import Image, ImageOps
ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT/'migration/media_manifest.json').read_text(encoding='utf8'))
for entry in manifest.values():
    if 'error' in entry: continue
    source = Image.open(ROOT/'media'/entry['original'])
    has_alpha = 'A' in source.getbands() or 'transparency' in source.info
    source = ImageOps.exif_transpose(source).convert('RGBA' if has_alpha else 'RGB')
    for size, field in [(640,'small'),(1200,'image')]:
        image=source.copy(); image.thumbnail((size,1000)); image.save(ROOT/'media'/entry[field],'WEBP',quality=82,method=6)
    token=Path(entry['image']).name.removesuffix('-1200.webp')
    for size,field in [(640,'card_small'),(960,'card_image')]:
        width=min(size,source.width,int(source.height*1.55));height=round(width/1.55)
        image=ImageOps.fit(source,(width,height))
        target=f'cars/webp/{token}-card-{size}.webp';image.save(ROOT/'media'/target,'WEBP',quality=76,method=6);entry[field]=target
        if size==960:entry['card_width'],entry['card_height']=image.size
(ROOT/'migration/media_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
print('Responsive WebP rebuilt from local originals; alpha retained.')
