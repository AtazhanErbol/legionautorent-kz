import secrets


class SelectedCityMiddleware:
    """Remember a visitor's city independently of a page's SEO/location data."""
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from locations.models import City
        request.selected_city = None
        if not request.path.startswith(('/' + settings.ADMIN_PATH, '/healthz/', '/static/', '/media/')):
            cities = list(City.objects.filter(active=True).prefetch_related('translations'))
            request.nav_cities = cities
            explicit = request.GET.get('city')
            page_path = getattr(request, 'base_path', request.path)
            chosen = next((city for city in cities if city.slug == explicit), None)
            if chosen is None and page_path != '/':
                chosen = next((city for city in cities if city.legacy_path == page_path), None)
            if chosen is not None and request.session.get('selected_city') != chosen.slug:
                request.session['selected_city'] = chosen.slug
            saved = request.session.get('selected_city')
            request.selected_city = chosen or next((city for city in cities if city.slug == saved), None)
        return self.get_response(request)


class CanonicalHostMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        from django.conf import settings
        from django.http import HttpResponsePermanentRedirect
        from urllib.parse import urlsplit
        if settings.CANONICAL_HOST_REDIRECT and request.path != '/healthz/':
            canonical = urlsplit(settings.SITE_URL)
            if request.get_host().lower() != canonical.netloc.lower():
                return HttpResponsePermanentRedirect(settings.SITE_URL + request.get_full_path())
        return self.get_response(request)

class ContentSecurityPolicyMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        request.csp_nonce=secrets.token_urlsafe(24)
        response=self.get_response(request)
        script=f"'self' 'wasm-unsafe-eval' 'nonce-{request.csp_nonce}' https://www.googletagmanager.com https://www.google-analytics.com https://mc.yandex.ru"
        response['Content-Security-Policy']='; '.join([
            "default-src 'self'",f'script-src {script}',"style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob: https://mc.yandex.ru https://www.google-analytics.com",
            "font-src 'self'", "connect-src 'self' https://*.google-analytics.com https://*.googletagmanager.com https://mc.yandex.ru",
            "frame-src https://yandex.ru https://www.googletagmanager.com", "media-src 'self' blob:", "worker-src 'self' blob:",
            "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"
        ])
        response['Referrer-Policy']='strict-origin-when-cross-origin'
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        return response
