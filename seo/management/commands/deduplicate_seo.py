"""Owner-authorized duplicate correction, never modifies URLs or catalogue facts."""
import json
from collections import defaultdict
from pathlib import Path
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from cars.models import Car
from seo.editorial import normalized


class Command(BaseCommand):
    help='Preview duplicate SEO corrections; --apply records exact before/after values and updates only duplicate fields.'
    def add_arguments(self,parser): parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        manifest=Path(settings.BASE_DIR)/'migration/seo_editorial_overrides.json'
        existing=json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else {'authorization':'Owner requested correcting the 52 duplicate groups on 2026-10-05; exact URLs, canonical, body and catalogue data retained.','pages':{}}
        cars=list(Car.objects.public().prefetch_related('cities'))
        changes={}
        groups_count=0
        for field,attr in [('title','seo_title'),('description','seo_description'),('h1','seo_h1')]:
            groups=defaultdict(list)
            for car in cars:groups[normalized(getattr(car,attr)).casefold()].append(car)
            duplicates=[group for value,group in groups.items() if value and len(group)>1]
            groups_count+=len(duplicates)
            candidates={}
            for group in duplicates:
                for car in group:
                    cities=', '.join(city.name for city in car.cities.all())
                    if field=='title':value=f'{car.name} — аренда, {cities} | Legion'
                    elif field=='h1':value=f'Аренда {car.name} — {cities}'
                    else:
                        price=f'{int(car.base_price):,}'.replace(',',' ')
                        value=f'Аренда {car.name} без водителя. {cities}. От {price} ₸ в сутки. Фото, тарифы и условия Legion Auto Rent.'
                    candidates[car.pk]=value
            counts=defaultdict(int)
            for car in cars:counts[normalized(candidates.get(car.pk,getattr(car,attr))).casefold()]+=1
            for car in cars:
                if car.pk not in candidates:continue
                value=candidates[car.pk]
                if counts[normalized(value).casefold()]>1:
                    value=(value+f' Автомобиль №{car.pk}.') if field=='description' else (value+f' · авто №{car.pk}')
                changes.setdefault(car.legacy_path,{})[field]={'before':getattr(car,attr),'after':value}
        if options['apply'] and changes:
            for path,fields in changes.items():
                if path in existing['pages']:raise CommandError('An earlier editorial change already exists for this URL; review it manually in CMS.')
            with transaction.atomic():
                for car in cars:
                    fields=changes.get(car.legacy_path,{})
                    if not fields:continue
                    for field,item in fields.items():setattr(car,'seo_'+field,item['after'])
                    car.save(update_fields=['seo_'+field for field in fields]+['updated_at'])
                existing['pages'].update(changes)
                manifest.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        report={'applied':bool(options['apply']),'duplicate_groups':groups_count,'pages':len(changes),'fields':sum(len(v) for v in changes.values()),'changes':changes}
        (Path(settings.BASE_DIR)/'reports/seo_duplicate_changes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        self.stdout.write(json.dumps({key:value for key,value in report.items() if key!='changes'},ensure_ascii=False))
