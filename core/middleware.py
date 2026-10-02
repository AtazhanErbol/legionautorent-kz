import secrets

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
            "frame-src https://yandex.ru https://www.googletagmanager.com", "media-src 'self'", "worker-src 'self' blob:",
            "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"
        ])
        response['Referrer-Policy']='strict-origin-when-cross-origin'
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        return response
