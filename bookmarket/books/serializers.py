from django.db.models import Avg
from rest_framework import serializers

from .models import Book, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class BookSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    favorite_count = serializers.IntegerField(read_only=True)
    image = serializers.ImageField(read_only=True)
    seller_rating = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'description',
            'price',
            'condition',
            'condition_display',
            'image',
            'is_sold',
            'created_at',
            'category',
            'category_name',
            'seller',
            'seller_username',
            'seller_rating',
            'favorite_count',
        ]
        read_only_fields = ['is_sold', 'created_at', 'seller']

    def get_seller_rating(self, obj):
        """Satıcının ortalama puanı (değerlendirme yoksa null)."""
        avg = obj.seller.received_reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 2) if avg is not None else None


class BookCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author', 'description', 'price', 'condition', 'category', 'image']
