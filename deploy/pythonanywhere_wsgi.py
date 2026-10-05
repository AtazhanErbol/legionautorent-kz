"""Template for the WSGI file linked from PythonAnywhere's Web tab.

Replace YOUR_USERNAME below. This file does not deploy or reload anything.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path('/home/YOUR_USERNAME/legionautorent.kz')
env_file = PROJECT_ROOT / '.env.pythonanywhere'
if not env_file.is_file():
    raise RuntimeError('Create the private .env.pythonanywhere file first.')
sys.path.insert(0, str(PROJECT_ROOT))
os.environ['LEGION_ENV_FILE'] = str(env_file)
load_dotenv(env_file, override=True)
if os.environ.get('ENVIRONMENT') not in ('staging', 'production'):
    raise RuntimeError('PythonAnywhere must use staging or production settings.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'legion.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
