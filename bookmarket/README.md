# BookMarket — İkinci El Kitap Pazarı

ACM412 Web Programming dönem projesi. Django 4.2 + DRF + Bootstrap 5 ile geliştirilmiş, kullanıcıların ikinci el kitap ilanı verip alıp satabildiği, mesajlaşabildiği ve favorilerini yönetebildiği tam donanımlı bir pazaryeri uygulaması.

## Hızlı Başlangıç

```bash
cd bookmarket
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser     # opsiyonel — admin paneli için
python manage.py seed_simulation     # opsiyonel — demo veri
python manage.py runserver
```

- Uygulama: <http://127.0.0.1:8000/>
- Admin paneli: <http://127.0.0.1:8000/admin/>
- REST API: <http://127.0.0.1:8000/api/books/>

Demo kullanıcılar (seed sonrası): `demo_ali`, `demo_ayse`, `demo_can`, `demo_defne` — şifre `demo1234`.

## Özellikler

### Temel
- **Kitap CRUD** — listeleme, detay, oluştur, düzenle, sil; sil/düzenle yalnızca ilan sahibi
- **Kategori & durum** — yeni gibi / iyi / yıpranmış filtreleri
- **Görsel yükleme** — `ImageField` + Pillow
- **Sipariş akışı** — `transaction.atomic` + `select_for_update` ile yarış-koşulu güvenli satın alma
- **Kullanıcı sistemi** — kayıt, giriş, çıkış, profil sayfası

### Gelişmiş (rubric Bölüm 4)
1. **Authentication** — Django built-in auth + özelleştirilmiş `UserRegisterForm`
2. **Authorization** — ilan sahibi/alıcı/satıcı bazlı görünürlük ve eylem kontrolü
3. **Search & Filter** — başlık/yazar araması + kategori + durum + fiyat aralığı
4. **Pagination** — kitap listesinde 9'arlı sayfalama
5. **REST API (DRF)** — `/api/books/`, `/api/categories/`, custom `favorite` action
6. **AJAX** — favori toggle (kalp butonu), mesaj iş parçacığında canlı gönderme
7. **Favoriler (M2M)** — kullanıcı–kitap ManyToMany ilişkisi, favori listesi

### UX
- **Dark mode** — sistem tercihini algılar, localStorage ile kalıcı, tek tıkla geçiş
- **Animasyonlar** — kart hover, kalp animasyonu, mesaj balon geçişi
- **Responsive** — Bootstrap 5 grid + mobil navbar; 320 px'e kadar test edildi
- **Hero banner** — anasayfada CSS gradient ile öne çıkan başlık

## Mimari ve Modeller

```
bookmarket/
├── bookmarket/      # Proje ayarları, ana URL'ler, WSGI/ASGI
├── books/           # Ana uygulama: Book, Category, Message, Order
│   ├── models.py
│   ├── views.py     # HTML view'lar (book CRUD, mesajlar, favoriler)
│   ├── api_views.py # DRF ViewSet'leri
│   ├── serializers.py
│   ├── api_urls.py  # /api/ rotaları
│   ├── urls.py      # HTML rotaları
│   ├── forms.py
│   ├── admin.py
│   └── management/commands/seed_simulation.py
├── users/           # Kayıt, giriş, profil
├── templates/       # base + books/* + users/*
├── static/          # css/app.css, js/app.js (dark mode + AJAX)
└── media/           # Yüklenen kitap görselleri
```

### Veri Modeli

| Model | Alanlar | İlişkiler |
|---|---|---|
| `Category` | name, slug | — |
| `Book` | title, author, description, price, condition, image, is_sold, created_at | FK→User (seller), FK→Category, M2M→User (favorited_by) |
| `Message` | body, sent_at | FK→User (sender, receiver), FK→Book |
| `Order` | address, ordered_at | OneToOne→Book, FK→User (buyer) |

- `Book.Meta.ordering = ['-created_at']` ve `(is_sold, -created_at)` üzerinde composite index — liste sayfası için optimize.
- Tüm ilan listelerinde `select_related('category', 'seller')` ile N+1 sorgu yok.
- API'da `annotate(favorite_count=Count('favorited_by'))` ile favori sayısı tek sorguda.

### Sipariş yarış-koşulu güvenliği

[`order_create`](books/views.py) içinde `transaction.atomic` + `Book.objects.select_for_update()` kullanılır. İki kullanıcı aynı anda satın almaya çalışırsa, ikincisi satılmış kitap mesajı görür.

### REST API

| Endpoint | Method | Auth | Açıklama |
|---|---|---|---|
| `/api/books/` | GET | Açık | Liste — `?q=`, `?category=`, `?condition=`, `?is_sold=` |
| `/api/books/` | POST | Auth | Yeni ilan (satıcı = istek sahibi) |
| `/api/books/{id}/` | GET | Açık | Detay |
| `/api/books/{id}/` | PUT/PATCH | Sahip | Güncelle |
| `/api/books/{id}/` | DELETE | Sahip | Sil |
| `/api/books/{id}/favorite/` | POST | Auth | Favori toggle, `{favorited, favorite_count}` döner |
| `/api/categories/` | GET | Açık | Kategori listesi |

Browsable API: <http://127.0.0.1:8000/api/books/> (Django session auth).

### AJAX akışı

- **Favori toggle**: `static/js/app.js` global listener — `.btn-favorite[data-toggle-url]` öğesine tıklanınca CSRF token ile POST atar, UI'ı server cevabına göre günceller.
- **Canlı mesaj**: `message_thread` template'inde `<form data-ajax-message>` — `fetch` ile gönderir, başarılı yanıtta yeni baloncuk DOM'a eklenir (sayfa yenilemesiz).

## Test

```bash
python manage.py test books
```

18 test geçer (book CRUD, izin, satın alma, fiyat filtresi, favoriler, AJAX mesaj, REST API, kullanıcı kaydı).

```bash
python manage.py seed_simulation
```

Demo veri ekler ve uçtan uca senaryoyu (satın alma, mesajlaşma, yetki kontrolü) test eder.

## Tasarım kararları

- **Django 4.2 LTS**: hedef ortamın Python 3.9 olması ve LTS desteği (Nisan 2028'e kadar) nedeniyle 5.x yerine 4.2 tercih edildi.
- **DRF SessionAuth**: ek bir token altyapısı kurmak yerine, browsable API'nin doğrudan kullanılabilir olması için session-based auth.
- **WhiteNoise**: production'da ayrı bir static dosya sunucusu gerektirmeden Render üzerinde çalışsın diye. `DEBUG=False` iken `CompressedManifestStaticFilesStorage` etkin.
- **CSS değişkenleri ile dark mode**: JS sadece `data-theme` attribute'ünü değiştirir; tüm renkler `var(--bm-*)` üzerinden, böylece her yere ekstra class eklemek gerekmez.
- **AJAX tercihi**: heavy JS framework yerine vanilla `fetch` — bağımlılık eklemeden iki-üç dosyada bitiyor.

## Deployment (Render)

`render.yaml` ve `build.sh` projeyle birlikte gelir. Yeni bir Render Web Service oluşturup repo'yu bağlamak yeterli — `DATABASE_URL` otomatik enjekte edilir (Postgres add-on), `DJANGO_SECRET_KEY` ve `DJANGO_DEBUG=False` env vars set edilmelidir.

```bash
# Manuel doğrulama (lokal):
DJANGO_DEBUG=False .venv/bin/python manage.py collectstatic --noinput
DJANGO_DEBUG=False .venv/bin/gunicorn bookmarket.wsgi
```

Ayrıntılar: [DEPLOYMENT.md](DEPLOYMENT.md).

## Üretim öncesi kontrol listesi

- [ ] `DJANGO_SECRET_KEY` env değişkeni set edilmiş
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` veya `RENDER_EXTERNAL_HOSTNAME` set
- [ ] `python manage.py migrate` çalıştırılmış
- [ ] `python manage.py collectstatic --noinput` çalıştırılmış
- [ ] PostgreSQL bağlanmış (`DATABASE_URL`)

## Lisans

Akademik dönem projesi — eğitim amaçlı.
