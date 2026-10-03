"""Build and verify the two self-hosted fonts used by the night-garage UI."""
import hashlib
import json
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = 'ӘҒҚҢӨҰҮҺІәғқңөұүһі₸'
rows = []
for source, target, weights in [
    ('assets/font-review/montserrat/Montserrat[wght].ttf', 'static/fonts/montserrat-site.woff2', 600),
    ('static/fonts/GolosText.ttf', 'static/fonts/golos-night.woff2', (400, 600)),
]:
    font = TTFont(ROOT / source)
    options = subset.Options()
    options.flavor = 'woff2'
    options.layout_features = ['*']
    options.name_IDs = ['*']
    worker = subset.Subsetter(options=options)
    worker.populate(unicodes=list(range(0x20, 0x250)) + list(range(0x400, 0x530)) + list(range(0x2000, 0x2070)) + [0x20b8, 0x20ac, 0x2116, 0x2122, 0x2197, 0x2212])
    worker.subset(font)
    instantiateVariableFont(font, {'wght': weights}, inplace=True)
    font.flavor = 'woff2'
    font.save(ROOT / target)
    final = TTFont(ROOT / target)
    missing = [c for c in REQUIRED if ord(c) not in final.getBestCmap()]
    assert not missing, (target, missing)
    data = (ROOT / target).read_bytes()
    rows.append({'source': source, 'file': target, 'weights': weights, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'required': REQUIRED, 'missing': missing, 'glyphs': len(final.getBestCmap())})
(ROOT / 'static/fonts/Montserrat-OFL.txt').write_bytes((ROOT / 'assets/font-review/montserrat/OFL.txt').read_bytes())
(ROOT / 'reports/night_fonts.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(rows, ensure_ascii=False))
