import csv
import json
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from cars.models import Car,CarBrand,CarCategory,CarImage,CarDiscount
from locations.models import City
from core.models import SiteSettings
from importer.source import catalogue_source

class Command(BaseCommand):
    help='Idempotent legacy import: extracted data reused, live/raw SEO and prices authoritative.'
    def add_arguments(self,parser):
        parser.add_argument('--source',help='Normalized export adapter; otherwise use preserved repo catalogue.')
        parser.add_argument('--dry-run',action='store_true')
        parser.add_argument('--download-images',action='store_true')
    def handle(self,*args,**options):
        data,improvements=catalogue_source(options['source'])
        root=settings.BASE_DIR;reports=root/'reports';reports.mkdir(exist_ok=True)
        differences=[]
        for item in data['cars']:
            existing=Car.objects.filter(legacy_path=item['legacy_path']).first()
            differences.append({'path':item['legacy_path'],'db_price':str(existing.base_price) if existing else '',
                                'live_price':item['base_price'],'price_changed':bool(existing and existing.base_price!=Decimal(item['base_price'])),
                                'db_public':existing.active if existing else '', 'live_public':item.get('active',True),
                                'availability_changed':bool(existing and not existing.active),'availability_note':'Public page/listing only; no realtime availability calendar exposed.'})
        with (reports/'price_availability_diff.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(differences[0]));writer.writeheader();writer.writerows(differences)
        if options['dry_run']:
            self.stdout.write(json.dumps({'dry_run':True,'cars':len(data['cars']),'cities':len(data['cities']),'price_changes':sum(d['price_changed'] for d in differences),'availability_changes':sum(d['availability_changed'] for d in differences)}));return
        # Populate preserved extracted images/taxonomy, then apply the explicit source authority.
        call_command('migrate_legion_data',source=options['source'] or str(root/'migration/normalized.json'),download_images=options['download_images'],stdout=self.stdout)
        updated=0
        with transaction.atomic():
            for item in data['cities']:
                city=City.objects.get(legacy_path=item['legacy_path'])
                fields=['slug','seo_title','seo_description','seo_h1','canonical_url','body','og_title','og_description','og_image','hero_text','legacy_meta']
                changes=[field for field in fields if field in item and getattr(city,field)!=item[field]]
                for field in changes:setattr(city,field,item[field])
                if changes:city.save(update_fields=changes+['updated_at'])
            for item in data['cars']:
                car=Car.objects.get(legacy_path=item['legacy_path'])
                fields=['slug','name','base_price','seo_title','seo_description','seo_h1','canonical_url','description','og_title','og_description','og_image','active','accepts_requests','legacy_meta']
                changes=[field for field in fields if field in item and getattr(car,field)!=item[field]]
                for field in changes:setattr(car,field,item[field])
                if changes:car.save(update_fields=changes+['updated_at']);updated+=1
            site=SiteSettings.objects.get(pk=1)
            live_path=root/'migration/rebuild/live_audit.json'
            if live_path.exists():
                from bs4 import BeautifulSoup
                live=json.loads(live_path.read_text(encoding='utf8'));home=next(p for p in live['pages'] if p['path']=='/')
                soup=BeautifulSoup((root/'migration/rebuild/snapshot'/home['snapshot_file']).read_text(encoding='utf8'),'html.parser')
                for field,name in [('google_verification','google-site-verification'),('yandex_verification','yandex-verification')]:
                    node=soup.find('meta',attrs={'name':name})
                    if node:setattr(site,field,node.get('content',''))
                for field,key in [('gtm_id','gtm'),('ga4_id','ga4'),('metrika_id','metrika')]:
                    values=home.get('analytics',{}).get(key,[])
                    if values:setattr(site,field,values[0])
                site.map_url=City.objects.get(legacy_path='/').map_url
                site.save()
        report={'cars':Car.objects.count(),'cities':City.objects.count(),'images':CarImage.objects.count(),'updated_records':updated,
                'price_changes':sum(d['price_changed'] for d in differences),'availability_changes':sum(d['availability_changed'] for d in differences),
                'authority':'live/raw snapshots for slug and SEO; live public prices and presence','improvements':improvements,
                'slugs_regenerated':False,'source_data_deleted':False}
        (reports/'import_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        self.stdout.write(json.dumps({k:v for k,v in report.items() if k!='improvements'},ensure_ascii=True))
