"""
Demo verisi: birkaç kullanıcı, ilan, satın alma ve mesaj akışı.
Çalıştır: python manage.py seed_simulation
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.test import Client

from books.models import Book, Category, Message, Order

TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
    b"\x02D\x01\x00;"
)

DEMO_USERNAMES = ("demo_ali", "demo_ayse", "demo_can", "demo_defne")


def _save_book_image(book: Book, name: str) -> None:
    book.image.save(name, ContentFile(TINY_GIF), save=True)


class Command(BaseCommand):
    help = "Demo kullanıcılar, ilanlar, satın alma ve mesaj senaryosu oluşturur."

    def handle(self, *args, **options):
        self.stdout.write("Eski demo kullanıcıları temizleniyor (varsa)...")
        User.objects.filter(username__in=DEMO_USERNAMES).delete()

        cat, _ = Category.objects.get_or_create(
            slug="demo-roman",
            defaults={"name": "Demo Roman"},
        )

        ali = User.objects.create_user("demo_ali", "ali@demo.local", "demo1234")
        ayse = User.objects.create_user("demo_ayse", "ayse@demo.local", "demo1234")
        can = User.objects.create_user("demo_can", "can@demo.local", "demo1234")
        defne = User.objects.create_user("demo_defne", "defne@demo.local", "demo1234")

        self.stdout.write(self.style.SUCCESS("4 demo kullanıcı oluşturuldu (şifre: demo1234)."))

        b_ali = Book(
            seller=ali,
            category=cat,
            title="Ali — Kürk Mantolu Madonna",
            author="Sabahattin Ali",
            description="İyi durumda, notlu.",
            price=Decimal("120.00"),
            condition="good",
        )
        b_ali.save()
        _save_book_image(b_ali, "ali.gif")

        b_ayse = Book(
            seller=ayse,
            category=cat,
            title="Ayşe — Simyacı",
            author="Coelho",
            description="Az kullanılmış.",
            price=Decimal("85.00"),
            condition="new",
        )
        b_ayse.save()
        _save_book_image(b_ayse, "ayse.gif")

        b_can = Book(
            seller=can,
            category=cat,
            title="Can — Suç ve Ceza",
            author="Dostoyevski",
            description="Ciltli baskı.",
            price=Decimal("200.00"),
            condition="used",
        )
        b_can.save()
        _save_book_image(b_can, "can.gif")

        b_defne = Book(
            seller=defne,
            category=cat,
            title="Defne — 1984",
            author="Orwell",
            description="İngilizce baskı.",
            price=Decimal("95.00"),
            condition="good",
        )
        b_defne.save()
        _save_book_image(b_defne, "defne.gif")

        self.stdout.write(self.style.SUCCESS("Her kullanıcı için 1 ilan eklendi."))

        # Senaryo 1: Ali, Ayşe'nin kitabını satın alır
        with transaction.atomic():
            locked = Book.objects.select_for_update().get(pk=b_ayse.pk)
            assert not locked.is_sold
            assert not Order.objects.filter(book=locked).exists()
            Order.objects.create(
                buyer=ali,
                book=locked,
                address="Kadıköy, İstanbul (demo)",
            )
            locked.is_sold = True
            locked.save(update_fields=["is_sold"])

        b_ayse.refresh_from_db()
        assert b_ayse.is_sold
        self.stdout.write(self.style.SUCCESS("Satın alma: demo_ali → Ayşe'nin ilanı (OK)."))

        # Senaryo 2: Can, Defne'ye kitap hakkında yazar; Defne yanıtlar
        Message.objects.create(
            sender=can,
            receiver=defne,
            book=b_defne,
            body="Merhaba, kitabın kaçıncı baskı?",
        )
        Message.objects.create(
            sender=defne,
            receiver=can,
            book=b_defne,
            body="2019 baskısı, yazılar tertemiz.",
        )
        self.stdout.write(self.style.SUCCESS("Mesajlaşma: demo_can ↔ demo_defne (2 mesaj, OK)."))

        # HTTP: giriş + satın alma sayfası (hâlâ satışta kitap)
        client = Client()
        assert client.login(username="demo_can", password="demo1234")
        r = client.get(f"/book/{b_defne.pk}/satin-al/")
        assert r.status_code == 200
        r2 = client.post(
            f"/book/{b_defne.pk}/satin-al/",
            {"address": "Çankaya, Ankara (HTTP test)"},
            follow=True,
        )
        assert r2.status_code == 200
        b_defne.refresh_from_db()
        assert b_defne.is_sold
        self.stdout.write(self.style.SUCCESS("HTTP: demo_can Defne'nin kitabını satın aldı (OK)."))

        # Kendi ilanına satın alma denemesi → 403
        assert client.login(username="demo_ali", password="demo1234")
        r3 = client.get(f"/book/{b_ali.pk}/satin-al/")
        assert r3.status_code == 403
        self.stdout.write(self.style.SUCCESS("HTTP: kendi ilanına satın alma engellendi (403, OK)."))

        # Satılmış ilana tekrar satın alma → yönlendirme / hata mesajı
        r4 = client.get(f"/book/{b_ayse.pk}/satin-al/")
        assert r4.status_code in (302, 403)
        self.stdout.write(self.style.SUCCESS("HTTP: satılmış ilana tekrar erişim engellendi (OK)."))

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Tarayıcıda dene:"))
        self.stdout.write("  Giriş: /users/login/  → demo_ali / demo1234 (veya demo_ayse, demo_can)")
        self.stdout.write("  Admin: /admin/       → mevcut admin hesabın")
        self.stdout.write("  Mesajlar: /mesajlar/")
