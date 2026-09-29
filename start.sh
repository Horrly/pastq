#!/usr/bin/env bash
# Render start: migrate, add starter universities, then serve.
set -o errexit
cd backend

python manage.py migrate --noinput
python manage.py seed_universities

# Generous timeout: an AI explanation can take ~20s on a slow free tier.
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 4 --timeout 120 --access-logfile -
