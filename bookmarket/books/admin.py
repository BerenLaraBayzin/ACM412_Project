from django.contrib import admin
from .models import Category, Book, Order, Message

# Modelleri admin paneline tek tek kaydediyoruz
admin.site.register(Category)
admin.site.register(Book)
admin.site.register(Order)
admin.site.register(Message)