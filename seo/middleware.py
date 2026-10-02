from django.conf import settings
from django.http import HttpResponse
from .models import Redirect

class SEOMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        redirect = None
        if request.method in ('GET', 'HEAD') and not request.path.startswith(('/static/', '/media/', '/admin/')):
            redirect = Redirect.objects.filter(old_path=request.path, active=True).first()
        if redirect:
            response = HttpResponse(status=redirect.status_code)
            response['Location'] = redirect.new_path
        else:
            response = self.get_response(request)
        if settings.IS_STAGING or getattr(request, 'base_path', request.path).startswith(('/admin/', '/booking/', '/request-success/')):
            response['X-Robots-Tag'] = 'noindex, nofollow' if settings.IS_STAGING else 'noindex, follow'
        return response
