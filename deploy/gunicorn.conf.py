import os
bind='127.0.0.1:8001'
workers=int(os.getenv('WEB_CONCURRENCY','3'))
worker_class='gthread'
threads=2
timeout=30
max_requests=1000
max_requests_jitter=100
accesslog='-'
errorlog='-'
capture_output=True
# Only the local, trusted Nginx proxy may provide forwarded protocol headers.
forwarded_allow_ips='127.0.0.1'
