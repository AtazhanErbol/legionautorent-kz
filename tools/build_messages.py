"""Compile checked-in, manually authored Django UI translations (no machine translation)."""
import json
import re
from pathlib import Path
import polib

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'locale/ui_translations.json').read_text(encoding='utf8'))
for index, lang in enumerate(['kk', 'en']):
    target = ROOT / 'locale' / lang / 'LC_MESSAGES'; target.mkdir(parents=True, exist_ok=True)
    catalog = polib.POFile()
    catalog.metadata = {'Project-Id-Version':'Legion Auto Rent', 'Language':lang, 'Content-Type':'text/plain; charset=UTF-8', 'Plural-Forms':'nplurals=2; plural=(n != 1);'}
    for original, values in data.items(): catalog.append(polib.POEntry(msgid=original, msgstr=values[index]))
    catalog.save(str(target / 'django.po')); catalog.save_as_mofile(str(target / 'django.mo'))
keys = {m for f in (ROOT/'templates').rglob('*.html') for m in re.findall(r"\{% trans '([^']+)'",f.read_text(encoding='utf8'))}
for folder in ['core','cars','bookings']:
    for f in (ROOT/folder).glob('*.py'): keys.update(re.findall(r"_\('([^']+)'",f.read_text(encoding='utf8')))
missing = sorted(keys-set(data))
print(json.dumps({'translated_ui_strings':len(data),'missing':missing},ensure_ascii=True))
if missing: raise SystemExit(1)
