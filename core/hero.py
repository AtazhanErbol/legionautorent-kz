"""Presentation settings for the approved film; no SEO or catalogue mutations."""
from django.templatetags.static import static
from django.utils.translation import get_language
from core.i18n import get_translation


ASSETS = {
    'video': '/static/hero/hero-scrub-smooth60-c86f40f74879.mp4',
    'poster': '/static/hero/hero-poster-e9b496d7a585.webp',
    'mobile': '/static/hero/hero-static-27f030789025.webp',
    'ending': '/static/hero/hero-ending-87350d5b2b8d.webp',
}

CAPTIONS = {
    'ru': ('от 20 000 ₸ / сутки', 'Позвоните нам · Доставка в любую точку города · Договор за 10 минут'),
    'kk': ('тәулігіне 20 000 ₸ бастап', 'Бізге қоңырау шалыңыз · Қаланың кез келген жеріне жеткізу · 10 минутта шарт жасау'),
    'en': ('from 20 000 KZT per day', 'Call us · Delivery anywhere in the city · Contract in 10 minutes'),
}

def asset_url(path):
    return static(path.removeprefix('/static/')) if path.startswith('/static/') else path


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
    approved = site.hero_video_path == ASSETS['video']
    return {
        'video': asset_url(site.hero_video_path) if site.enable_hero_video else '',
        'poster': asset_url(poster),
        'mobile': asset_url(site.hero_mobile_poster_path or poster),
        'ending': asset_url(site.hero_ending_path) if site.hero_ending_path else '',
        'bytes': 3673288 if approved else 0,
        'fps': 60 if approved else 24,
        'width': 1280 if approved else 0,
        'height': 720 if approved else 0,
        **captions,
    }
