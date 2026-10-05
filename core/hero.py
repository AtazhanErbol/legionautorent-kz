"""Presentation settings for the approved film; no SEO or catalogue mutations."""
from django.templatetags.static import static


ASSETS = {
    'video': '/static/hero/mercedes-segment-01-43d4cc20ca42.mp4',
    'poster': '/static/hero/mercedes-front-77ca8545d4d0.webp',
    'mobile': '/static/hero/mercedes-front-mobile-940302853d4f.webp',
    'ending': '/static/hero/mercedes-ending-1f6aa0701c89.webp',
}

# A presentation derivative of the owner's source. CMS paths remain editable;
# custom uploads are served verbatim. The original approved master is retained.
SCRUB_VARIANT = '/static/hero/mercedes-segment-01-motion60-bdfa81f7498c.mp4'


def asset_url(path):
    return static(path.removeprefix('/static/')) if path.startswith('/static/') else path


def hero_context(site):
    poster = site.hero_poster_path or ASSETS['poster']
    optimized = site.hero_video_path == ASSETS['video']
    video = SCRUB_VARIANT if optimized else site.hero_video_path
    return {
        'video': asset_url(video) if site.enable_hero_video else '',
        'poster': asset_url(poster),
        'mobile': asset_url(site.hero_mobile_poster_path or poster),
        'ending': asset_url(site.hero_ending_path) if site.hero_ending_path else '',
        'bytes': 5120095 if optimized else 0,
        'fps': 60 if optimized else 24,
        'width': 1440 if optimized else 0,
        'height': 810 if optimized else 0,
    }
