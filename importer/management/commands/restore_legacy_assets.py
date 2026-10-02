import hashlib
import json
from pathlib import Path
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Restore the original video referenced by preserved Open Graph metadata.'

    def add_arguments(self, parser):
        parser.add_argument('--download', action='store_true')

    def handle(self, *args, **options):
        record = json.loads((settings.BASE_DIR / 'migration/rebuild/legacy_video.json').read_text(encoding='utf8'))
        target = Path(settings.MEDIA_ROOT) / 'legacy/video-2.mp4'
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == record['sha256']:
            self.stdout.write('Legacy video SHA256 verified.'); return
        if not options['download']:
            raise CommandError('Restore media/legacy/video-2.mp4 from backup or use restore_legacy_assets --download.')
        response = requests.get(record['source'], timeout=60)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != record['sha256']:
            raise CommandError('Legacy video changed upstream; inspect it before updating the manifest.')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        self.stdout.write('Original legacy video restored and verified.')
