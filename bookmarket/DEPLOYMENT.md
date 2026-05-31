# Deployment — Render

Bu doküman BookMarket'i Render.com üzerine deploy etme adımlarını anlatır.

## Önkoşullar

- GitHub'a push'lanmış proje
- Render hesabı (ücretsiz tier yeterli)

## 1. PostgreSQL veritabanı oluştur

Render Dashboard → **New** → **PostgreSQL**
- Name: `bookmarket-db`
- Region: `Frankfurt` (TR'ye yakın)
- Plan: **Free**

Oluşturulduktan sonra **Internal Database URL**'i not al — bir sonraki adımda gerekecek.

## 2. Web Service oluştur

Render Dashboard → **New** → **Web Service** → GitHub repo'yu seç.

| Alan | Değer |
|---|---|
| Name | `bookmarket` |
| Region | `Frankfurt` |
| Branch | `main` |
| Root Directory | `bookmarket` |
| Runtime | `Python 3` |
| Build Command | `./build.sh` |
| Start Command | `gunicorn bookmarket.wsgi` |
| Plan | **Free** |

## 3. Environment Variables

| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | Render'ın "Generate" düğmesi ile rastgele oluştur |
| `DJANGO_DEBUG` | `False` |
| `DATABASE_URL` | (PostgreSQL Internal URL — adım 1'den) |
| `WEB_CONCURRENCY` | `4` (opsiyonel, gunicorn worker sayısı) |
| `PYTHON_VERSION` | `3.12.4` |

`RENDER_EXTERNAL_HOSTNAME` Render tarafından otomatik enjekte edilir; `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS`'e kod tarafında ekleniyor.

## 4. Deploy

Save edip "Create Web Service"'e tıkla. İlk deploy ~3 dakika sürer:

1. `build.sh` çalışır:
   - `pip install -r requirements.txt`
   - `python manage.py collectstatic --noinput`
   - `python manage.py migrate --noinput`
2. Gunicorn 4 worker ile uygulamayı serve eder.
3. WhiteNoise static dosyaları (CSS/JS) compressed manifest storage ile sunar.

## 5. Superuser oluştur

Deploy sonrası Render Dashboard → Service → **Shell** sekmesinde:

```bash
python manage.py createsuperuser
```

Artık `/admin/` paneline kategori ekleyebilirsin.

## 6. Demo veri (opsiyonel)

```bash
python manage.py seed_simulation
```

## Mimari notlar

### WhiteNoise

Static dosyaları sunmak için ayrı bir CDN/storage'a ihtiyaç yok — `WhiteNoiseMiddleware` security middleware'den hemen sonra eklenmiş ve `STATIC_ROOT`'tan compressed manifest ile servis ediyor.

```python
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

`DEBUG=True` iken manifest storage devre dışıdır (testlerin geçmesi için).

### dj-database-url

`DATABASE_URL` set edildiğinde otomatik olarak PostgreSQL'e yönelir. Lokal'de SQLite, prod'da Postgres — kod değişikliği gerekmez.

```python
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(_database_url, conn_max_age=600)
```

### Güvenlik

`DEBUG=False` iken aktifleşir:
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER` — Render'ın HTTPS terminator'ü için

## Sorun giderme

| Hata | Çözüm |
|---|---|
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS`'e domain'i ekle |
| `static file not found` | Build log'da `collectstatic` çalıştı mı kontrol et |
| `CSRF verification failed` | `CSRF_TRUSTED_ORIGINS` doğru mu (https:// prefix ile) |
| Migration hatası | Shell'den `python manage.py migrate` manuel çalıştır |
