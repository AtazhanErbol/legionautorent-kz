"""Build a local review gallery from the actual final browser screenshots."""
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/playwright/hero-story-round3'
shots=[
    ('Начало — крупная типографика и фронтальный ракурс','1440x1000-p00.png'),
    ('Фары включаются по прокрутке','1440x1000-p12.png'),
    ('Кадр уменьшается влево, текст раскрывается справа','1440x1000-p33.png'),
    ('Асимметричная композиция деталей','1440x1000-p58.png'),
    ('Задний ракурс и существующий финальный текст','1440x1000-p82.png'),
    ('Выход к форме поиска','1440x1000-p96.png'),
    ('Переход в каталог без пустого промежутка','1440x1000-catalog-exit.png'),
    ('Карточка автомобиля крупно','card-closeup.png'),
    ('Телефон — первый экран','mobile390-first.png'),
    ('Телефон — доступный поиск','mobile390-search.png'),
    ('Телефон — последовательность деталей','mobile390-details.png'),
    ('Телефон — финальный ракурс','mobile390-rear.png'),
    ('Широкий экран 1920 px — ограниченный масштаб','1920x1080-p00.png'),
    ('Костанай, desktop','../visual-round-story-final/city-1440.png'),
    ('Костанай, mobile','../visual-round-story-final/city-390.png'),
    ('Автомобиль, desktop','../visual-round-story-final/car-1440.png'),
    ('Автомобиль, mobile','../visual-round-story-final/car-390.png'),
]
for _,name in shots:
    if not (OUT/name).is_file():raise FileNotFoundError(OUT/name)
figures=''.join(f'<figure><a href="{escape(name)}"><img loading="lazy" src="{escape(name)}" alt="{escape(label)}"></a><figcaption>{escape(label)}</figcaption></figure>' for label,name in shots)
page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Legion — пять сцен прокрутки</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#080a0b;color:#fff;font:16px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:48px 24px}h1{font-size:clamp(36px,5vw,68px);line-height:1.05;max-width:1000px}p{max-width:900px;color:#bbc0c4}a{color:#f7b500}h2{margin-top:56px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}figure{margin:0;padding:0;border:1px solid #ffffff20;background:#131516;align-self:start}img,video{display:block;width:100%;height:auto}figure img{max-height:780px;object-fit:contain;background:#080a0b}figcaption{padding:16px;font-size:14px}video{max-width:1280px;background:#000}details{margin:24px 0}summary{cursor:pointer;padding:16px;border:1px solid #ffffff20}details img{max-width:700px;margin:auto}@media(max-width:760px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}</style><main>
<p>LEGION AUTO RENT · 03.10.2026</p><h1>Один ролик.<br>Пять связанных сцен.</h1>
<p>Крупный фронт → уменьшение цельного студийного кадра влево → детали → задний ракурс → поиск. На компьютере прокрутка управляет временем и композицией, на телефонах — обычная последовательность блоков.</p>
<p><a href="http://127.0.0.1:8002/">Открыть сайт ↗</a> · <a href="../../../SCROLL_STORY_REPORT.md">Описание реализации</a></p>
<p>Исходник 1280×720. Масштаб ограничен, веб-ролик сохранён с меньшими потерями сжатия (CRF18). Он остаётся 720p: искусственная детализация не добавлялась. Скриншоты ниже сняты в браузере после этих изменений.</p>
<h2>Подготовленный ролик</h2><video controls muted playsinline preload="none" poster="../../../static/img/hero-drive-front.webp" src="../../../static/video/hero-drive.mp4"></video>
<details><summary>Открыть исходный GIF для сравнения композиционных переходов</summary><img loading="lazy" src="../../../assets/hero-film/source/1_LQmQdk96lvRuSXW5LSJVBA.gif" alt="Предоставленный референс анимации"></details>
<h2>Состояния и страницы</h2><div class="grid">'''+figures+'''</div><p>374 браузерные проверки, 60 Django-тестов и 122 старых URL проверены. Метрики и ограничения: PERFORMANCE_REPORT.md и TEST_REPORT.md. Это локальная версия, production не переключался.</p></main></html>'''
(OUT/'index.html').write_text(page,encoding='utf8')
print(OUT/'index.html')
