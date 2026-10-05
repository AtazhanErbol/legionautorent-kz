import hashlib
import json
from collections import Counter
from pathlib import Path
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction
from django.apps import apps

APPS={'core','locations','cars','pages','seo'}

class Command(BaseCommand):
    help='Validate a portable content export; --apply imports only into an empty business database.'
    def add_arguments(self,parser):
        parser.add_argument('fixture')
        parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        target=Path(options['fixture']).resolve()
        try:
            data=target.read_bytes()
            manifest=json.loads(target.with_suffix('.manifest.json').read_text(encoding='utf8'))
            rows=json.loads(data)
        except (OSError,ValueError) as exc: raise CommandError('Missing or invalid fixture/manifest.') from exc
        if hashlib.sha256(data).hexdigest()!=manifest.get('sha256'):raise CommandError('Checksum mismatch.')
        for row in rows:
            label=row.get('model','')
            if label.split('.')[0] not in APPS and label!='bookings.bookingrequest':raise CommandError('Unexpected model in content export.')
        if dict(Counter(row['model'] for row in rows))!=manifest.get('models'):raise CommandError('Model counts do not match manifest.')
        if not options['apply']:
            self.stdout.write('Checksum and model counts verified. No data changed.');return
        with transaction.atomic():
            for label in ['cars.Car','locations.City','pages.Page','bookings.BookingRequest']:
                if apps.get_model(label).objects.exists():raise CommandError('Target has business data. Restore into a fresh database; nothing was imported.')
            call_command('loaddata',str(target),verbosity=0)
        self.stdout.write('Content imported. Create a NEW administrator; local passwords were not transferred.')
