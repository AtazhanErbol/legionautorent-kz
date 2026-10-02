import os
import sys
import secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
if settings.ENVIRONMENT!='development':raise SystemExit('Only local development account creation is supported by this helper.')
User=get_user_model()
if User.objects.filter(username='legion_admin').exists():
    print('Local admin exists; its credentials were preserved.')
else:
    password=secrets.token_urlsafe(24)
    User.objects.create_superuser(username='legion_admin',email='',password=password)
    target=ROOT/'.local/admin-access.txt'
    target.parent.mkdir(exist_ok=True)
    target.write_text(f'Локальный Admin Legion Auto Rent\nURL: http://127.0.0.1:8002/admin/\nUsername: legion_admin\nPassword: {password}\n\nТолько для локальной разработки. Не использовать в production.\n',encoding='utf8')
    print('Local admin created. Credentials saved in ignored .local/admin-access.txt.')
