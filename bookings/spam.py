import hashlib
import hmac
import time
import ipaddress
from django.conf import settings
from django.db import models, transaction
from .models import RateLimitBucket

def allow_request(request):
    # Nginx must overwrite X-Real-IP; only a known loopback peer may supply it.
    address = request.META.get('REMOTE_ADDR', 'unknown')
    if settings.TRUST_PROXY_HEADERS and address in settings.TRUSTED_PROXY_IPS:
        try:address=str(ipaddress.ip_address(request.META.get('HTTP_X_REAL_IP','')))
        except ValueError:pass
    digest = hmac.new(settings.SECRET_KEY.encode(), address.encode(), hashlib.sha256).hexdigest()
    key = f'{digest}:{int(time.time() // 900)}'
    with transaction.atomic():
        bucket, _ = RateLimitBucket.objects.get_or_create(key=key)
        RateLimitBucket.objects.filter(pk=bucket.pk).update(hits=models.F('hits') + 1)
        bucket.refresh_from_db()
    return bucket.hits <= 5
