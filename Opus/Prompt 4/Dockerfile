FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home app && mkdir -p /app/staticfiles /data/media && chown -R app /app/staticfiles /data/media
USER app
ENV MEDIA_ROOT=/data/media
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && python manage.py collectstatic --noinput && exec gunicorn marketplace.wsgi -b 0.0.0.0:8000 -w ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile -"]
