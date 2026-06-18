"""Veri modelleri.

İlişkiler:
- ``Book.seller``        → ``User``        (ForeignKey, ilan sahibi)
- ``Book.category``      → ``Category``    (ForeignKey, opsiyonel)
- ``Book.favorited_by``  ↔ ``User``        (ManyToMany, favori ilişkisi)
- ``Message.sender/receiver/book`` (ForeignKey × 3)
- ``Order.book``         → ``Book``        (OneToOne — bir kitap bir kez satılır)
- ``Order.buyer``        → ``User``        (ForeignKey)
"""
from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Book(models.Model):
    CONDITION_CHOICES = [
        ('new', 'Yeni gibi'),
        ('good', 'İyi'),
        ('used', 'Yıpranmış'),
    ]
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='books')
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    image = models.ImageField(upload_to='book_images/')
    is_sold = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    favorited_by = models.ManyToManyField(
        User, related_name='favorite_books', blank=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_sold', '-created_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def original_price(self):
        """Sıfır kitap fiyatı tahmini — ikinci el indirimi göstermek için."""
        from decimal import Decimal
        multiplier = {
            'new':  Decimal('1.30'),
            'good': Decimal('1.55'),
            'used': Decimal('1.90'),
        }.get(self.condition, Decimal('1.40'))
        raw = self.price * multiplier
        return (raw.quantize(Decimal('1')) // Decimal('5')) * Decimal('5') + Decimal('5')

    @property
    def discount_percent(self):
        if not self.original_price or self.original_price <= self.price:
            return 0
        return int(round((1 - (float(self.price) / float(self.original_price))) * 100))

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender} to {self.receiver} about {self.book.title}"

class Order(models.Model):
    """Bir kitabın satın alma kaydı: teslimat, ödeme ve kargo bilgileri.

    Sipariş yaşam döngüsü ``status`` ile izlenir:
    hazırlanıyor → kargoya verildi → dağıtımda → teslim edildi.
    Her durum değişikliği ayrıca ``ShipmentEvent`` olarak kaydedilir
    (kargo takip ekranındaki zaman çizelgesi).
    """
    PAYMENT_CHOICES = [
        ('card', 'Kredi/Banka Kartı'),
        ('cod', 'Kapıda Ödeme'),
    ]
    STATUS_CHOICES = [
        ('preparing', 'Hazırlanıyor'),
        ('shipped', 'Kargoya verildi'),
        ('in_transit', 'Dağıtımda'),
        ('delivered', 'Teslim edildi'),
        ('cancelled', 'İptal edildi'),
    ]
    # Sıralı akış — zaman çizelgesinde tamamlanmış adımları işaretlemek için.
    STATUS_FLOW = ['preparing', 'shipped', 'in_transit', 'delivered']
    CARRIERS = [
        ('Yurtiçi Kargo', 'YK'),
        ('Aras Kargo', 'AK'),
        ('MNG Kargo', 'MNG'),
        ('PTT Kargo', 'PTT'),
        ('Sürat Kargo', 'SK'),
    ]
    FREE_SHIPPING_THRESHOLD = 150
    SHIPPING_FEE = 39

    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='purchases'
    )
    book = models.OneToOneField(
        Book, on_delete=models.CASCADE, related_name='sale_order'
    )
    # Teslimat bilgileri
    full_name = models.CharField(max_length=120, blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    city = models.CharField(max_length=80, blank=True, default='')
    address = models.TextField()
    # Ödeme
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default='card'
    )
    card_last4 = models.CharField(max_length=4, blank=True, default='')
    shipping_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    # Kargo / durum
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='preparing'
    )
    carrier = models.CharField(max_length=40, blank=True, default='')
    tracking_number = models.CharField(max_length=30, blank=True, default='')
    ordered_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def __str__(self):
        return f"Order: {self.book.title} by {self.buyer.username}"

    @property
    def total(self):
        return self.book.price + self.shipping_fee

    @property
    def is_trackable(self):
        return self.status in ('shipped', 'in_transit', 'delivered')

    @property
    def timeline(self):
        """Zaman çizelgesi için adım listesi: her adım done/current/future."""
        if self.status == 'cancelled':
            return []
        try:
            current_index = self.STATUS_FLOW.index(self.status)
        except ValueError:
            current_index = 0
        steps = []
        for idx, key in enumerate(self.STATUS_FLOW):
            steps.append({
                'key': key,
                'label': dict(self.STATUS_CHOICES)[key],
                'done': idx < current_index,
                'current': idx == current_index,
            })
        return steps


class ShipmentEvent(models.Model):
    """Bir siparişin kargo geçmişindeki tekil durum kaydı (takip ekranı)."""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='events'
    )
    status = models.CharField(max_length=12, choices=Order.STATUS_CHOICES)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order_id}: {self.get_status_display()}"


class Profile(models.Model):
    """Kullanıcının iletişim/teslimat bilgileri — ödeme ekranında ön doldurulur."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    city = models.CharField(max_length=80, blank=True, default='')
    address = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Profil: {self.user.username}"


class Review(models.Model):
    """Alıcının, satın aldığı kitabın satıcısına bıraktığı puan ve yorum.

    Her sipariş için en fazla bir değerlendirme yapılır (``order`` OneToOne).
    ``seller`` alanı ``order.book.seller`` ile aynıdır; satıcı bazlı ortalama
    puanı tek sorguda hesaplayabilmek için denormalize edilmiştir.
    """
    RATING_CHOICES = [(i, f"{i} yıldız") for i in range(1, 6)]

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='review'
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='given_reviews'
    )
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_reviews'
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reviewer} → {self.seller}: {self.rating}★"

    @property
    def stars(self):
        """Şablonda kolay döngü için dolu (True) / boş (False) yıldız listesi."""
        return [i <= self.rating for i in range(1, 6)]