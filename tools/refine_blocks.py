from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'core/views.py';text=path.read_text(encoding='utf8')
for kind in ['benefit','step','condition']:
    text=text.replace(f"ContentBlock.objects.filter(kind='{kind}', active=True).prefetch_related('translations')",f"content_blocks('{kind}')")
path.write_text(text,encoding='utf8')
print('Unpublished supporting content is hidden in KZ/EN.')
