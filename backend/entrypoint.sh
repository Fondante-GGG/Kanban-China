#!/bin/bash
set -e

echo "==> Running database migrations..."
python backend/manage.py migrate --noinput

echo "==> Collecting static files..."
python backend/manage.py collectstatic --noinput || true

echo "==> Checking if initial seed data is needed..."
python backend/seed_data.py || true

echo "==> Starting Daphne ASGI server on 0.0.0.0:8080..."
exec daphne -b 0.0.0.0 -p 8080 backend.config.asgi:application
