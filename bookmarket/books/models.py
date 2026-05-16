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
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender} to {self.receiver} about {self.book.title}"

class Order(models.Model):
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='purchases'
    )
    book = models.OneToOneField(
        Book, on_delete=models.CASCADE, related_name='sale_order'
    )
    address = models.TextField()
    ordered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order: {self.book.title} by {self.buyer.username}"