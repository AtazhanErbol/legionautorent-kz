"""Loopback-only production rendering for local Lighthouse. No external analytics."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['DEBUG']='false';os.environ['ENVIRONMENT']='production';os.environ['SECURE_SSL_REDIRECT']='false'
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise
from wsgiref.simple_server import make_server,WSGIServer
from socketserver import ThreadingMixIn
settings.SECURE_SSL_REDIRECT=False;settings.ANALYTICS_ENABLED=False
application=get_wsgi_application()
application=WhiteNoise(application,root=str(ROOT/'staticfiles'),prefix='static/',max_age=86400)
application.add_files(str(ROOT/'media'),prefix='media/')
class ThreadedServer(ThreadingMixIn,WSGIServer):daemon_threads=True
with make_server('127.0.0.1',8003,application,server_class=ThreadedServer) as server:
    print('Local audit only: http://127.0.0.1:8003/',flush=True);server.serve_forever()
