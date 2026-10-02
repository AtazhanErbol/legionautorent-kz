import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from django.core.management.base import BaseCommand
from cars.models import CarImage
from cars.images import generate_variants

class Command(BaseCommand):
    help='Add AVIF/WebP variants; never remove originals or existing image files.'
    def handle(self,*args,**options):
        groups={}
        for photo in CarImage.objects.all():groups.setdefault(photo.original.name,[]).append(photo)
        def build(entry):
            name,photos=entry;token=hashlib.sha256(name.encode()).hexdigest()[:20]
            return photos,generate_variants(photos[0].original.path,token)
        with ThreadPoolExecutor(max_workers=3) as pool:
            for count,(photos,variants) in enumerate(pool.map(build,groups.items()),1):
                CarImage.objects.filter(pk__in=[p.pk for p in photos]).update(variants=variants)
                if count%30==0:self.stdout.write(f'Optimized {count}/{len(groups)} original images')
        self.stdout.write(f'AVIF/WebP variants ready for {len(groups)} sources; originals retained.')
