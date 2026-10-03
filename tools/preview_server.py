"""Local-only WSGI preview with compressed static assets and cached media; always noindex."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['DEBUG']='false'
os.environ['ENVIRONMENT']='development'
os.environ['SECURE_SSL_REDIRECT']='false'
os.environ.setdefault('DJANGO_SETTINGS_MODULE','legion.settings')
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise
from wsgiref.simple_server import make_server
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer
class ThreadedServer(ThreadingMixIn,WSGIServer):daemon_threads=True
application=WhiteNoise(get_wsgi_application(),root=str(ROOT/'staticfiles'),prefix='static/',max_age=86400)
application.add_files(str(ROOT/'media'),prefix='media/')
with make_server('127.0.0.1',8002,application,server_class=ThreadedServer) as server:
    print('Local compressed preview http://127.0.0.1:8002/ — noindex',flush=True)
    server.serve_forever()
