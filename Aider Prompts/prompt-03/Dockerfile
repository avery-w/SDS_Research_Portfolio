FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" app
WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

ENV DJANGO_SETTINGS_MODULE=ecommerce.settings

USER app

CMD ["daphne","-b","0.0.0.0","-p","8000","ecommerce.asgi:application"]
