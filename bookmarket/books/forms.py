from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'category', 'description', 'price', 'condition', 'image']
        # Django bu alanlar için otomatik form oluşturacak.