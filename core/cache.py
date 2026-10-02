"""Anonymous page-context caching: render CSRF tokens and CSP nonces afresh."""
import hashlib
from django.conf import settings
from django.core.cache import cache

def page_context(request,build):
    if request.user.is_authenticated:return build()
    revision=cache.get('page_revision','initial')
    query=request.GET.copy()
    for key in list(query):
        if key.startswith('utm_') or key in ('gclid','yclid'):query.pop(key)
    digest=hashlib.sha256((request.path+'?'+query.urlencode()).encode()).hexdigest()
    key=f'page:{settings.IS_STAGING}:{settings.SITE_URL}:{revision}:{digest}'
    context=cache.get(key)
    if context is None:
        context=build();cache.set(key,context,settings.PAGE_CACHE_TIMEOUT)
    return context
