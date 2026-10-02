from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'static/css/site.css';text=path.read_text(encoding='utf8')
text=text.replace('color:#b6bec8;letter-spacing','color:#788596;letter-spacing')
text=text.replace('.language-switch a{color:var(--muted);padding-block:10px}', '.language-switch a{color:var(--muted);padding-block:10px;min-width:24px;text-align:center}')
path.write_text(text,encoding='utf8')
path=root/'templates/base.html';text=path.read_text(encoding='utf8');text=text.replace(' aria-label="Legion Auto Rent"','');text=text.replace('<span>LEGION<small>','<span>LEGION <small>');path.write_text(text,encoding='utf8')
print('Contrast, language hit areas and brand accessible label corrected.')
