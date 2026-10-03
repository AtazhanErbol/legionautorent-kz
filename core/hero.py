"""Presentation settings for the approved film; no SEO or catalogue mutations."""
from django.templatetags.static import static


ASSETS = {
    'video': '/static/hero/mercedes-segment-01-43d4cc20ca42.mp4',
    'poster': '/static/hero/mercedes-front-77ca8545d4d0.webp',
    'mobile': '/static/hero/mercedes-front-mobile-940302853d4f.webp',
    'ending': '/static/hero/mercedes-ending-1f6aa0701c89.webp',
}


def asset_url(path):
    return static(path.removeprefix('/static/')) if path.startswith('/static/') else path


def hero_context(site):
    poster = site.hero_poster_path or ASSETS['poster']
    return {
        'video': asset_url(site.hero_video_path) if site.enable_hero_video else '',
        'poster': asset_url(poster),
        'mobile': asset_url(site.hero_mobile_poster_path or poster),
        'ending': asset_url(site.hero_ending_path) if site.hero_ending_path else '',
        'bytes': 5546665 if site.hero_video_path == ASSETS['video'] else 0,
    }
