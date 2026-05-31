from django.contrib import admin

from .models import Book, Category, Message, Order


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'seller', 'category', 'price', 'condition', 'is_sold', 'created_at',
    )
    list_filter = ('condition', 'is_sold', 'category', 'created_at')
    search_fields = ('title', 'author', 'description')
    list_select_related = ('seller', 'category')
    autocomplete_fields = ('seller', 'category')
    readonly_fields = ('created_at',)
    filter_horizontal = ('favorited_by',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('book', 'buyer', 'ordered_at')
    list_filter = ('ordered_at',)
    search_fields = ('book__title', 'buyer__username')
    list_select_related = ('book', 'buyer')
    readonly_fields = ('ordered_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('book', 'sender', 'receiver', 'sent_at')
    list_filter = ('sent_at',)
    search_fields = ('body', 'sender__username', 'receiver__username', 'book__title')
    list_select_related = ('book', 'sender', 'receiver')
    readonly_fields = ('sent_at',)
