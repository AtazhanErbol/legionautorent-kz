FROM node:24-alpine AS assets
WORKDIR /build
COPY package.json package-lock.json vite.config.js ./
RUN npm ci --ignore-scripts
COPY frontend ./frontend
COPY static/fonts ./static/fonts
COPY static/hero/grain.webp ./static/hero/grain.webp
RUN npm run build

FROM python:3.12-slim-bookworm AS python-deps
WORKDIR /build
COPY requirements.lock ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.lock

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
COPY --from=python-deps /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.lock \
    && useradd --create-home --uid 10001 legion
COPY --chown=legion:legion . .
COPY --from=assets --chown=legion:legion /build/static/build ./static/build
RUN mkdir -p media staticfiles backups reports \
    && chown -R legion:legion media staticfiles backups reports \
    && chmod +x deploy/entrypoint.sh
USER legion
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=1200s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/healthz/',headers={'Host':'localhost'}),timeout=3)"
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn","--config","deploy/gunicorn.conf.py","legion.wsgi:application"]
