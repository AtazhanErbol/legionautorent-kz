"""Keep verified legacy media URLs usable after the domain switches servers."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponsePermanentRedirect


@lru_cache(maxsize=1)
def image_paths():
    manifest = json.loads((settings.BASE_DIR / 'migration/media_manifest.json').read_text(encoding='utf8'))
    return {urlsplit(url).path: value['original'] for url, value in manifest.items()}


def legacy_image(request, path):
    if path == 'legionautorent.svg':
        return FileResponse((settings.BASE_DIR / 'static/img/logo.svg').open('rb'), content_type='image/svg+xml')
    original = image_paths().get('/img/' + path)
    if not original:
        raise Http404()
    # Only paths in our checked-in source manifest are accepted; no filesystem input.
    return HttpResponsePermanentRedirect(settings.MEDIA_URL + original)


def legacy_video(request):
    path = Path(settings.MEDIA_ROOT) / 'legacy/video-2.mp4'
    if not path.is_file():
        raise Http404()
    return FileResponse(path.open('rb'), content_type='video/mp4')
