FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 legion
COPY --chown=legion:legion . .
RUN mkdir -p media staticfiles backups && chown -R legion:legion media staticfiles backups
USER legion
EXPOSE 8001
CMD ["gunicorn","legion.wsgi:application","--bind","0.0.0.0:8001","--workers","3","--threads","2","--access-logfile","-","--error-logfile","-"]
