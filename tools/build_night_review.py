"""Assemble the screenshot gallery and preserve raw verification evidence."""
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/playwright/night-garage-round3'
matrix = json.loads((ROOT / 'reports/night_garage_round3.json').read_text(encoding='utf8'))
city = json.loads((ROOT / 'reports/night_garage_city_type.json').read_text(encoding='utf8'))
corrections = {f"{row['language']}_{row['page']}_{row['width']}": row for row in city['layouts']}
resolved, remaining = [], []
for failure in matrix['failures']:
    correction = corrections.get(failure['check'])
    # Only the line-count failure was corrected; retain any other matrix failure.
    detail = failure['detail']
    typography_only = (detail['status'] == 200 and detail['h1'] == 1 and not detail['overflow']
                       and not detail['headerOverlap'] and not detail['clipped'])
    if correction and correction['passed'] and typography_only:
        resolved.append({'check': failure['check'], 'before': detail['h1Lines'], 'after': correction['lines']})
    else:
        remaining.append(failure)
remaining.extend(city['failures'])
final = {
    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    'source_reports': ['reports/night_garage_round3.json', 'reports/night_garage_city_type.json'],
    'changed_since_matrix': ['City H1 font-size only: account for headed Windows scrollbar width'],
    'matrix_layouts': len(matrix['layouts']), 'matrix_checks': len(matrix['checks']),
    'targeted_city_rechecks': len(city['layouts']), 'resolved_failures': resolved,
    'remaining_failures': remaining, 'errors': matrix['errors'],
    'passed': not remaining and not matrix['errors'],
}
(ROOT / 'reports/night_garage_final.json').write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding='utf8')

labels = [('home','Главная'),('city','Костанай'),('city-east','Усть-Каменогорск'),
          ('city-pavlodar','Павлодар'),('catalog','Автопарк'),('car','Автомобиль'),
          ('conditions','Условия'),('faq','Вопросы'),('contacts','Контакты'),
          ('booking','Заявка'),('callback','Обратный звонок'),('privacy','Конфиденциальность'),
          ('consent','Согласие'),('success','Подтверждение'),('404','Ошибка 404'),('500','Ошибка 500')]
html = ['''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Legion — утверждённый дизайн на всех страницах</title><style>
*{box-sizing:border-box}body{margin:0;background:#10100f;color:#f3f1e9;font:16px/1.6 system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:32px}a{color:#f7b500}h1{font-size:clamp(30px,4vw,56px);line-height:1.1}h2{margin-top:64px}p{color:#aaa99f}figure{margin:0;min-width:0}img{display:block;width:100%;height:auto;border:1px solid #55554b}figcaption{margin:12px 0 24px}.pair{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,1fr);gap:24px;align-items:start}.cards{display:flex;gap:24px;align-items:start}.cards figure{max-width:420px}nav{display:flex;gap:24px;flex-wrap:wrap}details{margin-top:48px;border-top:1px solid #55554b;padding-top:24px}summary{cursor:pointer;font-size:24px}@media(max-width:700px){main{padding:20px}.pair{grid-template-columns:1fr}.cards{flex-wrap:wrap}}
</style><main><p>LEGION AUTO RENT / 04.10.2026</p><h1>Утверждённый дизайн на всех страницах</h1>
<p>Настоящие снимки Chrome: 1440×900 и 390×844. Текущее видео сохранено; новое Higgsfield-видео ожидает отдельного согласования.</p>
<nav><a href="#home">Главная</a><a href="#city">Город</a><a href="#car">Автомобиль</a><a href="#cards">Карточка крупно</a><a href="#languages">KK / EN</a></nav>''']
def pair(language, name, label):
    result = [f'<h2 id="{name}">{escape(label)}</h2><div class="pair">']
    for width in (1440,390):
        image = f'{language}-{name}-{width}.png'
        full = f'{language}-{name}-{width}-full.png'
        if not (OUT / image).exists(): continue
        link = f' · <a href="{full}">Вся страница</a>' if (OUT / full).exists() else ''
        result.append(f'<figure><a href="{image}"><img loading="lazy" src="{image}" alt="{escape(label)} — {width} px"></a><figcaption>{width} px{link}</figcaption></figure>')
    return '\n'.join(result + ['</div>'])
for name, label in labels[:1]: html.append(pair('ru',name,label))
html.append('<h2 id="cards">Карточка крупно</h2><div class="cards">')
for width in (1440,390):
    html.append(f'<figure><img src="card-{width}.png" loading="lazy" alt="Карточка автомобиля"><figcaption>Экран {width} px</figcaption></figure>')
html.append('</div>')
for name, label in labels[1:]: html.append(pair('ru',name,label))
html.append('<h2 id="languages">Языковые версии</h2><p>Неполный перевод по-прежнему показывает предупреждение и остаётся закрыт от индексации.</p>')
for language in ('kk','en'):
    html.append(f'<details><summary>{language.upper()}</summary>')
    for name,label in labels: html.append(pair(language,name,label))
    html.append('</details>')
html.append('</main></html>')
(OUT / 'index.html').write_text('\n'.join(html), encoding='utf8')
print(json.dumps(final, ensure_ascii=False, indent=2))
