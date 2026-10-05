"""Portable content export without local accounts, sessions or credentials."""
import hashlib
import json
from pathlib import Path
from collections import Counter
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help='Export content and leads for a fresh PythonAnywhere database; existing files are never overwritten.'
    def add_arguments(self, parser): parser.add_argument('--output', required=True)
    def handle(self, *args, **options):
        target=Path(options['output']).resolve()
        if target.exists(): raise CommandError('Choose a fresh export filename.')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as stream:
            call_command('dumpdata','core','locations','cars','pages','seo','bookings.bookingrequest',use_natural_foreign_keys=True,use_natural_primary_keys=True,indent=2,stdout=stream)
        data=target.read_bytes()
        counts=Counter(row['model'] for row in json.loads(data))
        report={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'models':dict(counts),'accounts_exported':False,'includes_leads':True}
        target.with_suffix('.manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        try: target.chmod(0o600)
        except OSError: pass
        self.stdout.write(json.dumps(report,ensure_ascii=False,indent=2))
