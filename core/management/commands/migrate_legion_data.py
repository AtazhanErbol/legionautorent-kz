import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from cars.models import Car, CarBrand, CarCategory, CarImage, CarDiscount
from locations.models import City
from core.models import SiteSettings

class Command(BaseCommand):
    help = 'Idempotent import from saved legacy snapshot or normalized DB export.'
    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(settings.BASE_DIR / 'migration/normalized.json'))
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--refresh', action='store_true', help='Explicitly refresh existing CMS content from snapshot')
        parser.add_argument('--download-images', action='store_true', help='Download originals before import (requires network)')
    def handle(self, *args, **opts):
        source = Path(opts['source'])
        data = json.loads(source.read_text(encoding='utf8'))
        if opts['dry_run']:
            self.stdout.write(f"Plan: {len(data['cities'])} cities, {len(data['cars'])} cars; no writes.")
            return
        if opts['download_images']:
            import subprocess, sys
            subprocess.run([sys.executable, str(settings.BASE_DIR / 'tools/download_media.py')], check=True)
        manifest_path = settings.BASE_DIR / 'migration/media_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf8')) if manifest_path.exists() else {}
        result = {'created_cars': 0, 'updated_cars': 0, 'preserved_cars': 0, 'images': 0, 'missing_images': [], 'category_review_required': [], 'missing_characteristics': [], 'content_changes': data.get('content_changes', [])}
        categories = {}
        for order, (slug, name) in enumerate([('economy', 'Эконом'), ('comfort', 'Комфорт'), ('business', 'Бизнес'), ('suv', 'Внедорожники'), ('premium', 'Премиум')]):
            categories[slug], _ = CarCategory.objects.get_or_create(slug=slug, defaults={'name': name, 'sort_order': order, 'seo_title': f'Аренда автомобилей класса {name} | Legion Auto Rent', 'seo_h1': f'Автомобили класса {name}', 'seo_description': f'Выберите автомобиль класса {name} в Legion Auto Rent. Фотографии и стоимость аренды в тенге.'})
        for city_data in data['cities']:
            values = {k: v for k, v in city_data.items() if k != 'legacy_path'}
            if opts['refresh']: City.objects.update_or_create(legacy_path=city_data['legacy_path'], defaults=values)
            else: City.objects.get_or_create(legacy_path=city_data['legacy_path'], defaults=values)
        for car_data in data['cars']:
            with transaction.atomic():
                brand, _ = CarBrand.objects.get_or_create(name=car_data['brand'], defaults={'slug': slugify(car_data['brand'])})
                ignored = {'images', 'discounts', 'cities', 'brand', 'category', 'category_inferred'}
                values = {k: v for k, v in car_data.items() if k not in ignored and k != 'legacy_path'}
                values.update(brand=brand, category=categories[car_data['category']])
                method = Car.objects.update_or_create if opts['refresh'] else Car.objects.get_or_create
                car, created = method(legacy_path=car_data['legacy_path'], defaults=values)
                result['created_cars' if created else 'updated_cars' if opts['refresh'] else 'preserved_cars'] += 1
                if created or opts['refresh']:
                    car.cities.set(City.objects.filter(slug__in=car_data['cities']))
                    for discount in car_data['discounts']:
                        CarDiscount.objects.update_or_create(car=car, label=discount['label'], defaults=discount)
                for i, item in enumerate(car_data['images']):
                    media = manifest.get(item['url'])
                    if not media or 'error' in media:
                        result['missing_images'].append(item['url']); continue
                    values = {k: media[k] for k in ('original', 'image', 'small', 'width', 'height')}
                    values.update({k:media[k] for k in ('card_image','card_small','card_width','card_height') if k in media})
                    values.update(alt=item['alt'], sort_order=i)
                    image, added = CarImage.objects.get_or_create(car=car, legacy_url=item['url'], defaults={**values, 'is_main': i == 0 and not car.images.filter(is_main=True).exists()})
                    if opts['refresh']:
                        for k, v in values.items(): setattr(image, k, v)
                        image.save()
                    elif not image.card_image and media.get('card_image'):
                        for field in ('card_image','card_small','card_width','card_height'):setattr(image,field,media[field])
                        image.save(update_fields=['card_image','card_small','card_width','card_height'])
                    result['images'] += 1
                if car_data.get('category_inferred'): result['category_review_required'].append(car.legacy_path)
                result['missing_characteristics'].append(car.legacy_path)
        site, created = SiteSettings.objects.get_or_create(pk=1)
        if created or opts['refresh']:
            site.address = City.objects.get(legacy_path='/').address
            site.gtm_id = 'GTM-KJWPLLN'; site.ga4_id = 'G-00P3VJTEK9'; site.metrika_id = '92545653'
            site.google_verification = 'geTojAtAy867JOeFytBahU_LtDKIEE_k1n7ZntGWAFo'
            site.yandex_verification = '8f32e7708980b338'
            site.instagram = 'https://www.instagram.com/legionautorent.kz/'
            site.hero_car = Car.objects.filter(legacy_path='/car/toyota-camry-xv-80').first()
            hero = manifest.get('https://legionautorent.kz/img/car.png')
            if hero and 'error' not in hero: site.hero_image = hero['image']
            site.save()
        result['totals'] = {'cars': Car.objects.count(), 'cities': City.objects.count(), 'images': CarImage.objects.count()}
        (settings.BASE_DIR / 'data_migration_report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf8')
        self.stdout.write(self.style.SUCCESS(json.dumps(result['totals'])))
