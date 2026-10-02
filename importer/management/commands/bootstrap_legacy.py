import os,json
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from cars.models import Car,CarImage

class Command(BaseCommand):
    help='Populate only an empty installation; existing CMS databases are left intact.'
    def handle(self,*args,**options):
        marker=Path(settings.MEDIA_ROOT)/'.bootstrap-pending'
        if Car.objects.exists() and not marker.exists():
            self.stdout.write('Existing catalogue found; automatic import skipped.');return
        marker.parent.mkdir(parents=True,exist_ok=True)
        marker.write_text('Initial import in progress. Safe to retry bootstrap_legacy.\n',encoding='utf8')
        call_command('import_legacy',download_images=os.getenv('DOWNLOAD_LEGACY_IMAGES','false')=='true')
        source=json.loads((settings.BASE_DIR/'migration/normalized.json').read_text(encoding='utf8'))
        expected_images=sum(len(car['images']) for car in source['cars'])
        if CarImage.objects.count()!=expected_images:
            raise CommandError('The initial image import is incomplete. Check network/media errors and retry bootstrap_legacy.')
        missing=[photo.original.name for photo in CarImage.objects.all() if not Path(photo.original.path).is_file()]
        if missing:raise CommandError(f'{len(missing)} originals are missing; restore the media backup or run import_legacy --download-images.')
        call_command('restore_legacy_assets',download=os.getenv('DOWNLOAD_LEGACY_IMAGES','false')=='true')
        call_command('optimize_images');call_command('seed_content');call_command('seed_rebuild');call_command('setup_roles')
        marker.rename(marker.with_name('.bootstrap-complete'))
        self.stdout.write('Initial data loaded. Create an administrator with createsuperuser.')
