#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn witte_crm.wsgi:application \
  --bind 0.0.0.0:80 \
  --workers 3 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
