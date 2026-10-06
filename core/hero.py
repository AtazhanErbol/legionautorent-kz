"""Presentation settings and hashed URLs for the owner-supplied hero sequence."""
import json
from functools import lru_cache
from pathlib import Path
from django.conf import settings
from django.templatetags.static import static
from django.utils.translation import get_language
from core.i18n import get_translation


ASSETS = {
    'video': '/static/hero/hero-60fps.mp4',
    'mobile_video': '/static/hero/hero-60fps.mp4',
    'poster': '/static/hero/hero-poster-60fps-desktop.webp',
    'mobile': '/static/hero/hero-poster-60fps-mobile.webp',
    'ending': '/static/hero/hero-ending-60fps.webp',
}

CAPTIONS = {
    'ru': ('от 20 000 ₸ / сутки', 'Позвоните нам · Доставка в любую точку города · Договор за 10 минут'),
    'kk': ('тәулігіне 20 000 ₸ бастап', 'Бізге қоңырау шалыңыз · Қаланың кез келген жеріне жеткізу · 10 минутта шарт жасау'),
    'en': ('from 20 000 KZT per day', 'Call us · Delivery anywhere in the city · Contract in 10 minutes'),
}

def asset_url(path):
    return static(path.removeprefix('/static/')) if path.startswith('/static/') else path


@lru_cache(maxsize=8)
def read_sequence(path, modified):
    """Cache generated metadata, not hundreds of images or database content."""
    return json.loads(Path(path).read_text(encoding='utf8'))


def sequence_context(site):
    if not site.enable_hero_video:
        return {}
    video = site.hero_video_path
    if video.startswith('/static/'):
        folder = settings.BASE_DIR / 'static' / video.removeprefix('/static/')
    elif video.startswith('/media/'):
        folder = settings.MEDIA_ROOT / video.removeprefix('/media/')
    else:
        return {}
    # Generated manifests live beside the active master, including CMS uploads.
    manifest = folder.parent / 'sequence.json'
    try:
        data = read_sequence(str(manifest), manifest.stat().st_mtime_ns)
        if data['master'] != video:
            return {}
        return {'count': data['count'], 'fps': data['fps'], 'duration': data['duration'],
                'packSize': data['pack_size'], **{
                    name: {'width': data[name]['width'], 'height': data[name]['height'],
                           'bytes': data[name]['bytes'],
                           'packs': [asset_url(pack['url']) for pack in data[name]['packs']]}
                    for name in ('mobile', 'desktop')}}
    except (OSError, ValueError, KeyError):
        # A newly uploaded film is a usable static hero until its frames are built.
        return {}


def hero_context(site):
    poster = site.hero_poster_path or ASSETS['poster']
    language = get_language() or 'ru'
    translated = get_translation(site, language)
    defaults = CAPTIONS.get(language, CAPTIONS['ru'])
    captions = {}
    for index, field in enumerate(('hero_price_caption', 'hero_steps_caption')):
        owner = site if language == 'ru' else translated
        captions[field] = getattr(owner, field, '') or defaults[index]
    # Custom CMS assets are always served as selected, without substitution.
    sequence = sequence_context(site)
    approved = site.hero_video_path == ASSETS['video']
    return {
        'video': asset_url(site.hero_video_path) if site.enable_hero_video else '',
        'mobile_video': asset_url(site.hero_mobile_video_path or (ASSETS['mobile_video'] if approved else site.hero_video_path)) if site.enable_hero_video else '',
        'poster': asset_url(poster),
        'mobile': asset_url(site.hero_mobile_poster_path or poster),
        'ending': asset_url(site.hero_ending_path) if site.hero_ending_path else '',
        'sequence': sequence,
        'bytes': sequence.get('desktop', {}).get('bytes', 0),
        'fps': sequence.get('fps', site.hero_video_fps),
        'width': 1280 if approved else 0,
        'height': 720 if approved else 0,
        'alt': {'ru': 'Чёрный седан в тёмном шоуруме LEGIONAUTORENT',
                'kk': 'LEGIONAUTORENT қараңғы шоурумындағы қара седан',
                'en': 'Black sedan in the dark LEGIONAUTORENT showroom'}.get(language, 'LEGIONAUTORENT'),
        **captions,
    }
