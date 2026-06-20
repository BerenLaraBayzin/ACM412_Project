#!/usr/bin/env bash
# Render build script.
# Free tier has no Shell, so we run seed + superuser bootstrap during build.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Demo data — re-seed on every deploy because Render free tier has
# ephemeral disk: uploaded cover images get wiped between deploys, so
# we re-download them along with the demo data.
python manage.py rich_seed || echo "rich_seed step skipped/failed"

# Bootstrap/refresh superuser from env vars on every deploy.
# Şifreyi her zaman yeniden ayarlar — böylece repodaki eski db'de kalmış
# bir admin hesabı olsa bile giriş bilgileri env değerleriyle garanti edilir.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py shell <<EOF || echo "superuser bootstrap skipped"
from django.contrib.auth.models import User
u = "$DJANGO_SUPERUSER_USERNAME"
user, created = User.objects.get_or_create(
    username=u, defaults={"email": "$DJANGO_SUPERUSER_EMAIL"}
)
user.email = "$DJANGO_SUPERUSER_EMAIL"
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.set_password("$DJANGO_SUPERUSER_PASSWORD")
user.save()
print(f"Superuser {u} {'oluşturuldu' if created else 'şifresi güncellendi'}.")
EOF
fi
