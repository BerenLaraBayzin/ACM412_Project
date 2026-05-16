from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Book, Category
from .serializers import BookCreateSerializer, BookSerializer, CategorySerializer


class IsSellerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.seller_id == request.user.id


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class BookViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsSellerOrReadOnly]

    def get_queryset(self):
        qs = (
            Book.objects.select_related('category', 'seller')
            .annotate(favorite_count=Count('favorited_by'))
            .order_by('-created_at')
        )
        params = self.request.query_params
        q = params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q))
        category = params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        condition = params.get('condition')
        if condition in dict(Book.CONDITION_CHOICES):
            qs = qs.filter(condition=condition)
        is_sold = params.get('is_sold')
        if is_sold in ('true', 'false'):
            qs = qs.filter(is_sold=(is_sold == 'true'))
        return qs

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BookCreateSerializer
        return BookSerializer

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        book = self.get_object()
        user = request.user
        if book.favorited_by.filter(pk=user.pk).exists():
            book.favorited_by.remove(user)
            favorited = False
        else:
            book.favorited_by.add(user)
            favorited = True
        return Response(
            {'favorited': favorited, 'favorite_count': book.favorited_by.count()},
            status=status.HTTP_200_OK,
        )
