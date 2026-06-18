from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Book, Category, Message, Order, Review, ShipmentEvent


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
            {
                "full_name": "Ali Veli",
                "phone": "05551112233",
                "city": "İstanbul",
                "address": "Kadıköy Moda Cad. No:1",
                "payment_method": "cod",
            },
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        book.refresh_from_db()
        self.assertTrue(book.is_sold)
        order = Order.objects.get(book=book)
        self.assertEqual(order.status, "preparing")
        self.assertTrue(order.tracking_number)
        self.assertTrue(order.events.filter(status="preparing").exists())

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


class SortTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ali", password="testpass123")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.cheap = Book.objects.create(
            seller=self.user, category=self.cat, title="Ucuz Kitap", author="A",
            description="d", price=Decimal("10.00"), condition="good", image=_img(),
        )
        self.pricey = Book.objects.create(
            seller=self.user, category=self.cat, title="Pahalı Kitap", author="A",
            description="d", price=Decimal("500.00"), condition="good", image=_img(),
        )

    def test_sort_price_asc_orders_cheapest_first(self):
        r = self.client.get(reverse("book_list"), {"sort": "price_asc"})
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertLess(content.index("Ucuz Kitap"), content.index("Pahalı Kitap"))

    def test_sort_price_desc_orders_priciest_first(self):
        r = self.client.get(reverse("book_list"), {"sort": "price_desc"})
        content = r.content.decode()
        self.assertLess(content.index("Pahalı Kitap"), content.index("Ucuz Kitap"))

    def test_invalid_sort_falls_back(self):
        r = self.client.get(reverse("book_list"), {"sort": "bogus"})
        self.assertEqual(r.status_code, 200)


class ReviewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="satici", password="pass12345")
        self.buyer = User.objects.create_user(username="alici", password="pass12345")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat, title="Satılan Kitap", author="Y",
            description="d", price=Decimal("50.00"), condition="good",
            image=_img(), is_sold=True,
        )
        self.order = Order.objects.create(
            buyer=self.buyer, book=self.book, address="İstanbul",
        )

    def test_buyer_can_create_review(self):
        self.client.login(username="alici", password="pass12345")
        r = self.client.post(
            reverse("review_create", args=[self.order.pk]),
            {"rating": 5, "comment": "Harika satıcı"},
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        review = Review.objects.get(order=self.order)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.seller, self.seller)
        self.assertEqual(review.reviewer, self.buyer)

    def test_non_buyer_cannot_review(self):
        other = User.objects.create_user(username="yabanci", password="pass12345")
        self.client.login(username="yabanci", password="pass12345")
        r = self.client.post(
            reverse("review_create", args=[self.order.pk]),
            {"rating": 1, "comment": "x"},
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Review.objects.filter(order=self.order).exists())

    def test_review_updates_in_place(self):
        self.client.login(username="alici", password="pass12345")
        self.client.post(
            reverse("review_create", args=[self.order.pk]),
            {"rating": 3, "comment": " ilk"},
        )
        self.client.post(
            reverse("review_create", args=[self.order.pk]),
            {"rating": 5, "comment": "düzeltildi"},
        )
        self.assertEqual(Review.objects.filter(order=self.order).count(), 1)
        self.assertEqual(Review.objects.get(order=self.order).rating, 5)

    def test_seller_profile_shows_rating(self):
        Review.objects.create(
            order=self.order, reviewer=self.buyer, seller=self.seller,
            rating=4, comment="iyi",
        )
        r = self.client.get(reverse("seller_profile", args=[self.seller.username]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.seller.username)
        self.assertContains(r, "iyi")

    def test_seller_profile_404_for_unknown(self):
        r = self.client.get(reverse("seller_profile", args=["yokboyle"]))
        self.assertEqual(r.status_code, 404)


class CheckoutTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="satici", password="pass12345")
        self.buyer = User.objects.create_user(username="alici", password="pass12345")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat, title="Ucuz", author="Y",
            description="d", price=Decimal("40.00"), condition="good", image=_img(),
        )

    def _checkout(self, **overrides):
        data = {
            "full_name": "Ali Veli", "phone": "05551112233",
            "city": "İstanbul", "address": "Kadıköy",
            "payment_method": "card",
            "card_number": "4242 4242 4242 4242",
            "card_expiry": "09/27", "card_cvv": "123",
        }
        data.update(overrides)
        return self.client.post(reverse("order_create", args=[self.book.pk]), data)

    def test_card_checkout_charges_shipping_under_threshold(self):
        self.client.login(username="alici", password="pass12345")
        self._checkout()
        order = Order.objects.get(book=self.book)
        self.assertEqual(order.card_last4, "4242")
        # 40 ₺ < 150 ₺ eşik → kargo ücreti eklenir
        self.assertEqual(order.shipping_fee, Decimal(Order.SHIPPING_FEE))
        self.assertEqual(order.total, Decimal("40.00") + Decimal(Order.SHIPPING_FEE))

    def test_invalid_card_rejected(self):
        self.client.login(username="alici", password="pass12345")
        r = self._checkout(card_number="1234 5678 9012 3456")  # Luhn'a uymaz
        self.assertEqual(r.status_code, 200)  # form tekrar gösterilir
        self.assertFalse(Order.objects.filter(book=self.book).exists())
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_sold)

    def test_free_shipping_over_threshold(self):
        self.book.price = Decimal("200.00")
        self.book.save()
        self.client.login(username="alici", password="pass12345")
        self._checkout()
        order = Order.objects.get(book=self.book)
        self.assertEqual(order.shipping_fee, Decimal("0"))


class ShippingFlowTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="satici", password="pass12345")
        self.buyer = User.objects.create_user(username="alici", password="pass12345")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat, title="Kitap", author="Y",
            description="d", price=Decimal("90.00"), condition="good",
            image=_img(), is_sold=True,
        )
        self.order = Order.objects.create(
            buyer=self.buyer, book=self.book, address="İstanbul",
            status="preparing", carrier="Yurtiçi Kargo", tracking_number="YK123",
        )

    def test_seller_advances_status(self):
        self.client.login(username="satici", password="pass12345")
        self.client.post(reverse("order_advance", args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")
        self.assertIsNotNone(self.order.shipped_at)
        self.assertTrue(self.order.events.filter(status="shipped").exists())

    def test_buyer_cannot_advance(self):
        self.client.login(username="alici", password="pass12345")
        r = self.client.post(reverse("order_advance", args=[self.order.pk]))
        self.assertEqual(r.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "preparing")

    def test_order_detail_visible_to_buyer_and_seller(self):
        self.client.login(username="alici", password="pass12345")
        self.assertEqual(self.client.get(reverse("order_detail", args=[self.order.pk])).status_code, 200)
        self.client.login(username="satici", password="pass12345")
        self.assertEqual(self.client.get(reverse("order_detail", args=[self.order.pk])).status_code, 200)

    def test_order_detail_hidden_from_strangers(self):
        User.objects.create_user(username="yabanci", password="pass12345")
        self.client.login(username="yabanci", password="pass12345")
        r = self.client.get(reverse("order_detail", args=[self.order.pk]))
        self.assertEqual(r.status_code, 403)

    def test_cancel_while_preparing_frees_book(self):
        self.client.login(username="alici", password="pass12345")
        r = self.client.post(reverse("order_cancel", args=[self.order.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_sold)
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_cannot_cancel_after_shipped(self):
        self.order.status = "shipped"
        self.order.save()
        self.client.login(username="alici", password="pass12345")
        self.client.post(reverse("order_cancel", args=[self.order.pk]))
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())


class ExtraFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ali", password="testpass123", email="ali@x.com",
        )
        self.seller = User.objects.create_user(username="veli", password="pass12345")
        self.cat = Category.objects.create(name="Roman", slug="roman")
        self.book = Book.objects.create(
            seller=self.seller, category=self.cat, title="Kitap", author="Y",
            description="d", price=Decimal("50"), condition="good", image=_img(),
        )

    def test_detail_increments_views(self):
        start = self.book.views_count
        self.client.get(reverse("book_detail", args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.views_count, start + 1)

    def test_owner_view_not_counted(self):
        self.client.login(username="veli", password="pass12345")
        self.client.get(reverse("book_detail", args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.views_count, 0)

    def test_profile_edit_updates_user_and_profile(self):
        self.client.login(username="ali", password="testpass123")
        r = self.client.post(reverse("profile_edit"), {
            "first_name": "Ali", "last_name": "Veli", "email": "yeni@x.com",
            "phone": "05559998877", "city": "İzmir", "address": "Konak",
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ali")
        self.assertEqual(self.user.email, "yeni@x.com")
        self.assertEqual(self.user.profile.city, "İzmir")

    def test_static_pages_load(self):
        for name in ("about", "faq", "contact"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
