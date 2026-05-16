"""
Zengin demo verisi: çok sayıda kategori, kullanıcı, gerçek kitap ve kapak.

Çalıştır:
    python manage.py rich_seed
    python manage.py rich_seed --keep   # mevcut veriyi koru, sadece ekle
    python manage.py rich_seed --no-covers   # Open Library'den kapak indirme

Open Library Covers API kullanılır: https://covers.openlibrary.org/
ISBN bilinen kitaplar için public domain kapak görselleri çekilir.
"""

import random
import urllib.request
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book, Category, Message, Order


CATEGORIES = [
    ("Roman", "roman"),
    ("Felsefe", "felsefe"),
    ("Bilim & Teknoloji", "bilim-teknoloji"),
    ("Tarih", "tarih"),
    ("Şiir", "siir"),
    ("Polisiye", "polisiye"),
    ("Çocuk & Genç", "cocuk-genc"),
    ("Kişisel Gelişim", "kisisel-gelisim"),
]

# (title, author, isbn, category_slug, price, condition, description)
BOOKS = [
    # Roman
    ("1984", "George Orwell", "9780451524935", "roman", "85.00", "good",
     "Distopik klasik. Az okunmuş, kapağı yıpranmış değil."),
    ("Hayvan Çiftliği", "George Orwell", "9780451526342", "roman", "55.00", "new",
     "Cep baskı, neredeyse hiç açılmamış."),
    ("Suç ve Ceza", "Fyodor Dostoyevski", "9780486415871", "roman", "120.00", "good",
     "Ciltli baskı. İçeride önemli yerler işaretli (kurşunkalem)."),
    ("Karamazov Kardeşler", "Fyodor Dostoyevski", "9780374528379", "roman", "180.00", "good",
     "Çevirmen: Nihal Yalaza Taluy. İyi durumda."),
    ("Kürk Mantolu Madonna", "Sabahattin Ali", "9789754700565", "roman", "65.00", "new",
     "İletişim Yayınları, çok yeni."),
    ("Tutunamayanlar", "Oğuz Atay", "9789750802713", "roman", "210.00", "used",
     "Kült roman, kalın cilt. Kapak köşeleri yıpranmış."),
    ("Anna Karenina", "Lev Tolstoy", "9780143035008", "roman", "150.00", "good",
     "Penguin Classics, İngilizce. Aydınger sayfa ayracı dahil."),
    ("Yüzyıllık Yalnızlık", "Gabriel García Márquez", "9780060883287", "roman", "110.00", "good",
     "Büyülü gerçekçiliğin başyapıtı. Sayfa kıvrıkları az."),
    ("Sineklerin Tanrısı", "William Golding", "9780399501487", "roman", "75.00", "used",
     "Lise yıllarımdan kalma. Notlar var."),
    ("Otomatik Portakal", "Anthony Burgess", "9780393312836", "roman", "95.00", "good",
     "İngilizce orijinal baskı. Glossary dahil."),
    ("Beyaz Diş", "Jack London", "9781503215511", "roman", "45.00", "new",
     "Cep boy, hiç okunmamış gibi."),
    ("Bülbülü Öldürmek", "Harper Lee", "9780446310789", "roman", "90.00", "good",
     "Klasik Amerikan romanı. Kapağında küçük lekeler var."),

    # Felsefe
    ("Sofi'nin Dünyası", "Jostein Gaarder", "9780425152256", "felsefe", "130.00", "good",
     "Felsefeye giriş için klasik. Az notlu."),
    ("Böyle Buyurdu Zerdüşt", "Friedrich Nietzsche", "9780140441185", "felsefe", "100.00", "good",
     "Penguin Classics. Çok az altı çizili."),
    ("Devlet", "Platon", "9780872201361", "felsefe", "115.00", "used",
     "Cumhuriyet yayını. Yıpranmış ama tam."),
    ("Anlamın İzinde Yaşam", "Viktor Frankl", "9780807014295", "felsefe", "85.00", "new",
     "Logoterapinin temel kitabı, kullanılmamış gibi."),

    # Bilim & Teknoloji
    ("Zamanın Kısa Tarihi", "Stephen Hawking", "9780553380163", "bilim-teknoloji", "120.00", "good",
     "Türkçe baskı. Birkaç sayfa kıvrık."),
    ("Sapiens: Hayvanlardan Tanrılara", "Yuval Noah Harari", "9780062316097", "bilim-teknoloji", "140.00", "new",
     "Kolektif Kitap, neredeyse hiç açılmamış."),
    ("Bencil Gen", "Richard Dawkins", "9780198788607", "bilim-teknoloji", "110.00", "good",
     "Oxford baskı. Az altı çizili."),
    ("Clean Code", "Robert C. Martin", "9780132350884", "bilim-teknoloji", "350.00", "used",
     "Yazılım klasiği. Çalışırken çok kullandım, notlu."),
    ("Pragmatic Programmer", "Andrew Hunt & David Thomas", "9780201616224", "bilim-teknoloji", "300.00", "good",
     "İngilizce ilk baskı. İyi durumda."),
    ("Python Crash Course", "Eric Matthes", "9781593279288", "bilim-teknoloji", "220.00", "good",
     "Başlangıç düzeyi için harika. Tertemiz."),
    ("Introduction to Algorithms (CLRS)", "Cormen et al.", "9780262033848", "bilim-teknoloji", "650.00", "used",
     "Üçüncü baskı. Sırt biraz açık, içerik tamam."),

    # Tarih
    ("Nutuk", "Mustafa Kemal Atatürk", "9789753860451", "tarih", "150.00", "new",
     "Türk Tarih Kurumu baskı. Hiç açılmamış."),
    ("Osmanlı İmparatorluğu Klasik Çağ", "Halil İnalcık", "9789751607607", "tarih", "180.00", "good",
     "Türk tarihçiliğinin başyapıtlarından."),
    ("21. Yüzyıl İçin 21 Ders", "Yuval Noah Harari", "9781787330672", "tarih", "120.00", "new",
     "Çok yeni, hediye paketinden çıktı."),

    # Şiir
    ("Memleketimden İnsan Manzaraları", "Nazım Hikmet", "9789754700428", "siir", "85.00", "good",
     "YKY baskı. Sevdiğim şiirlerde sayfa katlı."),
    ("Sevda Sözleri", "Cemal Süreya", "9789750706103", "siir", "70.00", "new",
     "Toplu şiirler, küçük boy."),

    # Polisiye
    ("Doğu Ekspresinde Cinayet", "Agatha Christie", "9780062073631", "polisiye", "65.00", "good",
     "Klasik Christie. Sayfaları biraz sararmış."),
    ("Sherlock Holmes Bütün Maceraları", "Arthur Conan Doyle", "9780553212419", "polisiye", "200.00", "good",
     "Tek cilt, hepsi içinde. Kalın."),
    ("Kürk Mantolu Madonna'nın Sırrı", "Ahmet Ümit", "9789753428058", "polisiye", "75.00", "new",
     "Yeni baskı, neredeyse hiç açılmamış."),

    # Çocuk & Genç
    ("Şeker Portakalı", "José Mauro de Vasconcelos", "9789750714566", "cocuk-genc", "55.00", "good",
     "Klasik. Çocukluğumda okuduğum kopya."),
    ("Küçük Prens", "Antoine de Saint-Exupéry", "9780156012195", "cocuk-genc", "40.00", "new",
     "Resimli baskı, çok güzel durumda."),
    ("Hobbit", "J.R.R. Tolkien", "9780547928227", "cocuk-genc", "120.00", "good",
     "İngilizce, çocuk için ideal."),

    # Kişisel Gelişim
    ("Atomik Alışkanlıklar", "James Clear", "9780735211292", "kisisel-gelisim", "130.00", "new",
     "Tertemiz, ön kapakta hiç iz yok."),
    ("Düşünme Sanatı", "Rolf Dobelli", "9780062219695", "kisisel-gelisim", "95.00", "good",
     "Az notlu. Akıcı bir kitap."),
    ("Mindset", "Carol Dweck", "9780345472328", "kisisel-gelisim", "100.00", "good",
     "Türkçe çevirisi. İlk yarıda not var."),
]


# Demo kullanıcılar — her birine birkaç ilan dağıtılacak
DEMO_USERS = [
    ("demo_ali",    "Ali Yılmaz",    "ali@demo.local"),
    ("demo_ayse",   "Ayşe Demir",    "ayse@demo.local"),
    ("demo_can",    "Can Öztürk",    "can@demo.local"),
    ("demo_defne",  "Defne Aydın",   "defne@demo.local"),
    ("demo_emre",   "Emre Kaya",     "emre@demo.local"),
    ("demo_zeynep", "Zeynep Acar",   "zeynep@demo.local"),
]

DEMO_PASSWORD = "demo1234"


def _download_cover(isbn):
    """Open Library'den ISBN ile kapak çek. Yoksa None döner."""
    if not isbn:
        return None
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "BookMarket Seeder/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            # Open Library boş kapakta küçük yer tutucu döndürür; çok küçükse atla
            if len(data) < 500:
                return None
            return data
    except Exception:
        return None


# Görseli olmayan kitaplar için 1x1 GIF (model image alanı zorunlu)
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
    b"\x02D\x01\x00;"
)


class Command(BaseCommand):
    help = "Gerçekçi 30+ kitap, 6 kullanıcı, kategori ve örnek mesajlaşma ile dolu demo verisi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep", action="store_true",
            help="Mevcut demo veriyi silme; üzerine ekle.",
        )
        parser.add_argument(
            "--no-covers", action="store_true",
            help="Open Library'den kapak indirme (offline mod).",
        )

    def handle(self, *args, **options):
        keep = options["keep"]
        skip_covers = options["no_covers"]

        if not keep:
            self.stdout.write("Eski demo veriler temizleniyor...")
            User.objects.filter(username__in=[u[0] for u in DEMO_USERS]).delete()

        # Kategoriler
        cat_map = {}
        for name, slug in CATEGORIES:
            obj, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": name},
            )
            obj.name = name
            obj.save()
            cat_map[slug] = obj
        self.stdout.write(self.style.SUCCESS(f"{len(CATEGORIES)} kategori hazır."))

        # Kullanıcılar
        users = []
        for username, full_name, email in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": full_name.split()[0],
                          "last_name": " ".join(full_name.split()[1:])},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users.append(user)
        self.stdout.write(self.style.SUCCESS(
            f"{len(users)} demo kullanıcı (şifre: {DEMO_PASSWORD})."
        ))

        # Kitaplar
        random.seed(42)
        cover_hits = 0
        cover_misses = 0
        created_books = []
        with transaction.atomic():
            for i, (title, author, isbn, cat_slug, price, condition, desc) in enumerate(BOOKS):
                seller = users[i % len(users)]
                if Book.objects.filter(title=title, seller=seller).exists():
                    continue
                book = Book(
                    seller=seller,
                    category=cat_map.get(cat_slug),
                    title=title,
                    author=author,
                    description=desc,
                    price=Decimal(price),
                    condition=condition,
                )
                if not skip_covers:
                    cover = _download_cover(isbn)
                else:
                    cover = None
                if cover:
                    cover_hits += 1
                    book.image.save(f"{isbn}.jpg", ContentFile(cover), save=False)
                else:
                    cover_misses += 1
                    book.image.save(f"placeholder_{i}.gif", ContentFile(TINY_GIF), save=False)
                book.save()
                created_books.append(book)

        self.stdout.write(self.style.SUCCESS(
            f"{len(created_books)} kitap eklendi (kapak: {cover_hits} bulundu, {cover_misses} placeholder)."
        ))

        if not created_books:
            self.stdout.write(self.style.WARNING(
                "Yeni kitap eklenmedi (zaten mevcuttu). Mesajlaşma/favori sahnesi atlanıyor."
            ))
            return

        # Senaryo: bazı kitaplar satılsın
        for book in random.sample(created_books, k=min(5, len(created_books))):
            buyer = random.choice([u for u in users if u.id != book.seller_id])
            with transaction.atomic():
                locked = Book.objects.select_for_update().get(pk=book.pk)
                if locked.is_sold or Order.objects.filter(book=locked).exists():
                    continue
                Order.objects.create(
                    buyer=buyer, book=locked,
                    address=f"Demo adres — {buyer.first_name}",
                )
                locked.is_sold = True
                locked.save(update_fields=["is_sold"])
        self.stdout.write(self.style.SUCCESS("Birkaç kitap satılmış olarak işaretlendi."))

        # Favoriler
        for book in random.sample(created_books, k=min(12, len(created_books))):
            fans = random.sample(users, k=random.randint(1, 3))
            for u in fans:
                if u.id != book.seller_id:
                    book.favorited_by.add(u)
        self.stdout.write(self.style.SUCCESS("Rastgele favoriler eklendi."))

        # Mesajlaşma örneği
        for book in random.sample(
            [b for b in created_books if not b.is_sold],
            k=min(4, len([b for b in created_books if not b.is_sold])),
        ):
            buyer = random.choice([u for u in users if u.id != book.seller_id])
            Message.objects.create(
                sender=buyer, receiver=book.seller, book=book,
                body=f"Merhaba, {book.title} hâlâ satışta mı? Pazarlık şansı var mı?",
            )
            Message.objects.create(
                sender=book.seller, receiver=buyer, book=book,
                body="Merhaba, evet hâlâ satışta. Fiyatta küçük indirim yapabilirim.",
            )
        self.stdout.write(self.style.SUCCESS("Örnek mesajlaşmalar eklendi."))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Tarayıcıda dene:"))
        self.stdout.write(f"  Giriş: /users/login/  → demo_ali / {DEMO_PASSWORD}")
        self.stdout.write("  Admin: /admin/")
        self.stdout.write("  API:   /api/books/")
