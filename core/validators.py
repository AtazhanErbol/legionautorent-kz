from pathlib import Path
from django.core.exceptions import ValidationError
from PIL import Image

def validate_image(file):
    if file.size > 10 * 1024 * 1024: raise ValidationError('Изображение должно быть меньше 10 МБ.')
    try:
        file.seek(0)
        image = Image.open(file)
        if image.format not in ('JPEG', 'PNG', 'WEBP', 'AVIF'): raise ValueError()
        image.verify()
        file.seek(0)
    except Exception as exc:
        raise ValidationError('Допустимы только JPEG, PNG, WebP и AVIF.') from exc

def validate_glb(file):
    if file.size > 3 * 1024 * 1024: raise ValidationError('GLB должен быть меньше 3 МБ.')
    file.seek(0)
    import struct
    header=file.read(12)
    file.seek(0)
    if Path(file.name).suffix.lower() != '.glb' or len(header)!=12 or header[:4] != b'glTF' or struct.unpack_from('<II',header,4)!=(2,file.size): raise ValidationError('Нужен корректный GLB glTF 2.0.')
