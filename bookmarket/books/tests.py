from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Book, Category, Order


class BookViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.client = Client()
        self._tiny_gif = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02D\x01\x00;"
        )

    def test_book_list_200(self):
        response = self.client.get(reverse("book_list"))
        self.assertEqual(response.status_code, 200)

    def test_create_requires_login(self):
        url = reverse("book_create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create_book(self):
        self.client.login(username="ali", password="testpass123")
        image = SimpleUploadedFile(
            "test.gif", self._tiny_gif, content_type="image/gif"
        )
        response = self.client.post(
            reverse("book_create"),
            {
                "title": "Test Kitap",
                "author": "Yazar",
                "category": self.cat.pk,
                "description": "Açıklama",
                "price": "99.50",
                "condition": "good",
                "image": image,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        book = Book.objects.get(title="Test Kitap")
        self.assertEqual(book.seller, self.user)
        self.assertEqual(book.price, Decimal("99.50"))

    def test_book_list_search(self):
        self.client.login(username="ali", password="testpass123")
        image = SimpleUploadedFile(
            "x.gif", self._tiny_gif, content_type="image/gif"
        )
        self.client.post(
            reverse("book_create"),
            {
                "title": "Python Rehberi",
                "author": "Mehmet",
                "category": self.cat.pk,
                "description": "x",
                "price": "50",
                "condition": "good",
                "image": image,
            },
        )
        r = self.client.get(reverse("book_list"), {"q": "Python"})
        self.assertContains(r, "Python Rehberi")
        r2 = self.client.get(reverse("book_list"), {"q": "Java"})
        self.assertNotContains(r2, "Python Rehberi")

    def test_purchase_marks_sold(self):
        seller = User.objects.create_user(username="veli", password="pass12345")
        image = SimpleUploadedFile(
            "b.gif", self._tiny_gif, content_type="image/gif"
        )
        book = Book.objects.create(
            seller=seller,
            category=self.cat,
            title="Satılık",
            author="Y",
            description="d",
            price=Decimal("10.00"),
            condition="good",
            image=image,
        )
        self.client.login(username="ali", password="testpass123")
        url = reverse("order_create", args=[book.pk])
        r = self.client.post(
            url,
            {"address": "İstanbul Kadıköy"},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        book.refresh_from_db()
        self.assertTrue(book.is_sold)
        self.assertTrue(Order.objects.filter(book=book).exists())
