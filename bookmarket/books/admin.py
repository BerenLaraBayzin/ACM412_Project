from django.contrib import admin

from .models import Book, Category, Message, Order, Profile, Review, ShipmentEvent


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


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'book', 'buyer', 'status', 'carrier', 'tracking_number',
        'payment_method', 'ordered_at',
    )
    list_filter = ('status', 'payment_method', 'carrier', 'ordered_at')
    search_fields = ('book__title', 'buyer__username', 'tracking_number')
    list_select_related = ('book', 'buyer')
    readonly_fields = ('ordered_at',)
    inlines = [ShipmentEventInline]


@admin.register(ShipmentEvent)
class ShipmentEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__tracking_number', 'order__book__title')
    readonly_fields = ('created_at',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city')
    search_fields = ('user__username', 'phone', 'city')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('book', 'sender', 'receiver', 'sent_at')
    list_filter = ('sent_at',)
    search_fields = ('body', 'sender__username', 'receiver__username', 'book__title')
    list_select_related = ('book', 'sender', 'receiver')
    readonly_fields = ('sent_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('seller', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('seller__username', 'reviewer__username', 'comment')
    list_select_related = ('seller', 'reviewer', 'order')
    autocomplete_fields = ('order', 'reviewer', 'seller')
    readonly_fields = ('created_at',)
