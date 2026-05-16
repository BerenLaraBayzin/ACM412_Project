#!/usr/bin/env bash
# Render build script.
# Free tier has no Shell, so we run seed + superuser bootstrap during build.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Demo data — idempotent (--keep skips wipe, get_or_create on users/books)
python manage.py rich_seed --keep || echo "rich_seed step skipped/failed"

# Bootstrap superuser from env vars if they exist and account is missing
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py shell <<EOF || echo "superuser bootstrap skipped"
from django.contrib.auth.models import User
u = "$DJANGO_SUPERUSER_USERNAME"
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, "$DJANGO_SUPERUSER_EMAIL", "$DJANGO_SUPERUSER_PASSWORD")
    print(f"Superuser {u} oluşturuldu.")
else:
    print(f"Superuser {u} zaten var, atlandı.")
EOF
fi
