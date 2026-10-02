"""Generate additive AVIF/WebP variants while keeping uploaded originals intact."""
from pathlib import Path
from PIL import Image,ImageOps
from django.conf import settings

def generate_variants(source,token):
    image=source.copy() if isinstance(source,Image.Image) else Image.open(source)
    alpha='A' in image.getbands() or 'transparency' in image.info
    image=ImageOps.exif_transpose(image).convert('RGBA' if alpha else 'RGB')
    output=Path(settings.MEDIA_ROOT)/'cars/variants';output.mkdir(parents=True,exist_ok=True)
    variants={'avif':{},'card_avif':{},'webp':{}}
    for size in [480,960,1200]:
        frame=image.copy();frame.thumbnail((size,1000))
        for fmt,quality in [('avif',48),('webp',78)]:
            path=output/f'{token}-{size}.{fmt}'
            if not path.exists():frame.save(path,fmt.upper(),quality=quality)
            variants[fmt][str(frame.width)]=str(path.relative_to(settings.MEDIA_ROOT)).replace('\\','/')
    for size in [480,960]:
        width=min(size,image.width,int(image.height*1.55));height=max(1,round(width/1.55))
        frame=ImageOps.fit(image,(width,height));path=output/f'{token}-card-{size}.avif'
        if not path.exists():frame.save(path,'AVIF',quality=48)
        variants['card_avif'][str(width)]=str(path.relative_to(settings.MEDIA_ROOT)).replace('\\','/')
    return variants
