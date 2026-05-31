from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Book, Category, Message, Order


TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
    b"\x02D\x01\x00;"
)


def _img(name="t.gif"):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


class BookViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.client = Client()

    def test_book_list_200(self):
        response = self.client.get(reverse("book_list"))
        self.assertEqual(response.status_code, 200)

    def test_create_requires_login(self):
        response = self.client.get(reverse("book_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create_book(self):
        self.client.login(username="ali", password="testpass123")
        response = self.client.post(
            reverse("book_create"),
            {
                "title": "Test Kitap",
                "author": "Yazar",
                "category": self.cat.pk,
                "description": "Açıklama",
                "price": "99.50",
                "condition": "good",
                "image": _img(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        book = Book.objects.get(title="Test Kitap")
        self.assertEqual(book.seller, self.user)
        self.assertEqual(book.price, Decimal("99.50"))

    def test_book_list_search(self):
        self.client.login(username="ali", password="testpass123")
        self.client.post(
            reverse("book_create"),
            {
                "title": "Python Rehberi",
                "author": "Mehmet",
                "category": self.cat.pk,
                "description": "x",
                "price": "50",
                "condition": "good",
                "image": _img(),
            },
        )
        r = self.client.get(reverse("book_list"), {"q": "Python"})
        self.assertContains(r, "Python Rehberi")
        r2 = self.client.get(reverse("book_list"), {"q": "Java"})
        self.assertNotContains(r2, "Python Rehberi")

    def test_book_list_price_filter(self):
        Book.objects.create(
            seller=self.user, category=self.cat,
            title="Ucuz", author="A", description="d",
            price=Decimal("20.00"), condition="good", image=_img(),
        )
        Book.objects.create(
            seller=self.user, category=self.cat,
            title="Pahalı", author="A", description="d",
            price=Decimal("500.00"), condition="good", image=_img(),
        )
        r = self.client.get(reverse("book_list"), {"max_price": "100"})
        self.assertContains(r, "Ucuz")
        self.assertNotContains(r, "Pahalı")

    def test_owner_only_can_edit(self):
        intruder = User.objects.create_user(username="veli", password="pass12345")
        book = Book.objects.create(
            seller=self.user, category=self.cat,
            title="X", author="A", description="d",
            price=Decimal("10"), condition="good", image=_img(),
        )
        self.client.login(username="veli", password="pass12345")
        r = self.client.get(reverse("book_update", args=[book.pk]))
        self.assertEqual(r.status_code, 403)

    def test_purchase_marks_sold(self):
        seller = User.objects.create_user(username="veli", password="pass12345")
        book = Book.objects.create(
            seller=seller, category=self.cat,
            title="Satılık", author="Y", description="d",
            price=Decimal("10.00"), condition="good", image=_img(),
        )
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(
            reverse("order_create", args=[book.pk]),
            {"address": "İstanbul Kadıköy"},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        book.refresh_from_db()
        self.assertTrue(book.is_sold)
        self.assertTrue(Order.objects.filter(book=book).exists())

    def test_cannot_buy_own(self):
        book = Book.objects.create(
            seller=self.user, category=self.cat,
            title="Kendi", author="Y", description="d",
            price=Decimal("10"), condition="good", image=_img(),
        )
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(
            reverse("order_create", args=[book.pk]),
            {"address": "x"},
        )
        self.assertEqual(r.status_code, 403)


class FavoriteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")
        self.seller = User.objects.create_user(username="veli", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat,
            title="Favori Test", author="A", description="d",
            price=Decimal("30"), condition="good", image=_img(),
        )

    def test_favorite_toggle_requires_login(self):
        r = self.client.post(reverse("favorite_toggle", args=[self.book.pk]))
        self.assertEqual(r.status_code, 302)

    def test_favorite_toggle_add_and_remove(self):
        self.client.login(username="ali", password="testpass123")
        url = reverse("favorite_toggle", args=[self.book.pk])
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json(), {"favorited": True, "favorite_count": 1})
        self.assertTrue(self.book.favorited_by.filter(pk=self.user.pk).exists())
        r2 = self.client.post(url)
        self.assertEqual(r2.json(), {"favorited": False, "favorite_count": 0})

    def test_favorites_list_shows_favorited(self):
        self.client.login(username="ali", password="testpass123")
        self.book.favorited_by.add(self.user)
        r = self.client.get(reverse("favorites_list"))
        self.assertContains(r, "Favori Test")


class MessageAjaxTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username="ali", password="testpass123")
        self.seller = User.objects.create_user(username="veli", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat,
            title="Msg Test", author="A", description="d",
            price=Decimal("30"), condition="good", image=_img(),
        )

    def test_ajax_first_message_from_buyer(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(
            reverse("message_send_ajax", args=[self.book.pk, self.seller.pk]),
            {"body": "Merhaba"},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["body"], "Merhaba")
        self.assertEqual(data["sender"], "ali")
        self.assertEqual(Message.objects.count(), 1)

    def test_ajax_empty_rejected(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(
            reverse("message_send_ajax", args=[self.book.pk, self.seller.pk]),
            {"body": "   "},
        )
        self.assertEqual(r.status_code, 400)


class BookAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.user, category=self.cat,
            title="API Kitap", author="A", description="d",
            price=Decimal("42"), condition="good", image=_img(),
        )

    def test_api_book_list_public(self):
        r = self.client.get("/api/books/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreaterEqual(data["count"], 1)
        titles = [b["title"] for b in data["results"]]
        self.assertIn("API Kitap", titles)

    def test_api_book_detail_public(self):
        r = self.client.get(f"/api/books/{self.book.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title"], "API Kitap")

    def test_api_favorite_requires_auth(self):
        r = self.client.post(f"/api/books/{self.book.pk}/favorite/")
        self.assertIn(r.status_code, (401, 403))

    def test_api_favorite_toggles(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(f"/api/books/{self.book.pk}/favorite/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["favorited"])


class IsbnLookupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")

    def test_requires_login(self):
        r = self.client.get(reverse("isbn_lookup"), {"isbn": "9780451524935"})
        self.assertEqual(r.status_code, 302)

    def test_invalid_isbn(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.get(reverse("isbn_lookup"), {"isbn": "abc"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid_isbn")

    def test_empty_isbn(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.get(reverse("isbn_lookup"), {"isbn": ""})
        self.assertEqual(r.status_code, 400)

    def test_short_isbn(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.get(reverse("isbn_lookup"), {"isbn": "12345"})
        self.assertEqual(r.status_code, 400)


class ErrorPageTests(TestCase):
    def test_404_route(self):
        r = self.client.get("/bu-sayfa-yok/")
        self.assertEqual(r.status_code, 404)


class UserRegisterTests(TestCase):
    def test_register_creates_user(self):
        r = self.client.post(
            reverse("register"),
            {
                "username": "yeni",
                "email": "yeni@example.com",
                "password1": "Karmasik123!",
                "password2": "Karmasik123!",
            },
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(username="yeni").exists())
