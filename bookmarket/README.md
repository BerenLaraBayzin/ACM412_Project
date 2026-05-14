# İkinci El Kitap Pazarı (Bookmarket)

Django ile geliştirilen, kullanıcıların ikinci el kitap ilanı verebildiği basit bir pazar yeri uygulamasıdır.

## Özellikler

- Kitap ilanları: listeleme, detay, oluşturma, düzenleme, silme (CRUD; silme/düzenleme yalnızca ilan sahibi)
- Kategori ve durum (yeni gibi / iyi / yıpranmış) alanları
- Görsel yükleme (`ImageField`, Pillow gerekir)
- Kayıt, giriş, çıkış ve profil üzerinden kendi ilanlarını görüntüleme
- Temel birim testler (`books.tests`)

## Kurulum

```bash
cd bookmarket
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # isteğe bağlı — admin paneli için
python manage.py runserver
```

Tarayıcıda `http://127.0.0.1:8000/` adresine gidin. Yönetim paneli: `http://127.0.0.1:8000/admin/` — kategorileri buradan ekleyebilirsiniz.

## Mimari ve modeller

- **`books`**: `Category`, `Book` (satıcı `ForeignKey` → `User`), `Message` (alıcı–satıcı mesajı için taslak), `Order` (satın alma; `Book` ile `OneToOne`)
- **`users`**: Django’nun yerleşik `User` modeli; kayıt formu `UserCreationForm` türevi

Liste ve detay görünümlerinde `select_related` ile gereksiz sorgu sayısı azaltılmıştır.

## Geliştirme notları

- Üretimde `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` ve güvenli medya/sunucu ayarlarını yapılandırın.
- Gelişmiş notlar (REST API, arama, sayfalama, harici API) rubrik için ayrıca eklenebilir; `djangorestframework` bağımlılıkta yer alır, uç noktalar ihtiyaca göre tamamlanabilir.
