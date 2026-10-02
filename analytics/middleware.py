UTM_FIELDS = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')
from django.conf import settings

class AttributionMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if not request.path.startswith(('/static/', '/media/', '/img/', '/video/', '/'+settings.ADMIN_PATH, '/robots', '/sitemap','/healthz/')):
            if 'attribution' not in request.session:
                request.session['attribution'] = {'landing_page': request.path[:600], 'referrer': request.META.get('HTTP_REFERER', '')[:600], **{key: request.GET.get(key, '')[:200] for key in UTM_FIELDS}}
        return self.get_response(request)
