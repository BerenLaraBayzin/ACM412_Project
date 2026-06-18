import re

from django import forms
from .models import Book, Message, Order, Review


def _luhn_valid(number):
    """Kredi kartı numarası Luhn algoritmasına uygun mu?"""
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'category',
            'description',
            'price',
            'condition',
            'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5}
            ),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class OrderPurchaseForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['address']
        labels = {'address': 'Teslimat adresi'}
        widgets = {
            'address': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Teslimat adresiniz',
                }
            ),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        labels = {'body': 'Mesaj'}
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Mesajınızı yazın…',
                }
            ),
        }


class CheckoutForm(forms.ModelForm):
    """Ödeme + teslimat formu.

    Teslimat ve ödeme yöntemi modele (``Order``) yazılır. Kart bilgileri
    (numara/son kullanma/CVV) modelde saklanmaz — yalnızca biçim/Luhn
    doğrulaması yapılır ve son 4 hane ``card_last4`` olarak tutulur.
    """
    card_number = forms.CharField(
        required=False, label='Kart numarası',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'inputmode': 'numeric', 'autocomplete': 'cc-number',
            'placeholder': '4242 4242 4242 4242', 'maxlength': '23',
        }),
    )
    card_expiry = forms.CharField(
        required=False, label='Son kullanma (AA/YY)',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'autocomplete': 'cc-exp',
            'placeholder': 'AA/YY', 'maxlength': '5',
        }),
    )
    card_cvv = forms.CharField(
        required=False, label='CVV',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'inputmode': 'numeric', 'autocomplete': 'cc-csc',
            'placeholder': '123', 'maxlength': '4',
        }),
    )

    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'city', 'address', 'payment_method']
        labels = {
            'full_name': 'Ad Soyad',
            'phone': 'Telefon',
            'city': 'Şehir',
            'address': 'Teslimat adresi',
            'payment_method': 'Ödeme yöntemi',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad Soyad'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '05XX XXX XX XX'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'İstanbul'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mahalle, cadde, no, ilçe'}),
            'payment_method': forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('full_name', 'phone', 'city', 'address'):
            self.fields[name].required = True
        self.card_last4 = ''

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('payment_method') != 'card':
            return cleaned

        raw = re.sub(r'\s+', '', cleaned.get('card_number', ''))
        if not raw.isdigit() or not (13 <= len(raw) <= 19) or not _luhn_valid(raw):
            self.add_error('card_number', 'Geçerli bir kart numarası girin.')
        else:
            self.card_last4 = raw[-4:]

        expiry = (cleaned.get('card_expiry') or '').strip()
        if not re.match(r'^(0[1-9]|1[0-2])/\d{2}$', expiry):
            self.add_error('card_expiry', 'AA/YY biçiminde girin (örn. 09/27).')

        cvv = (cleaned.get('card_cvv') or '').strip()
        if not re.match(r'^\d{3,4}$', cvv):
            self.add_error('card_cvv', 'CVV 3-4 haneli olmalı.')

        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        labels = {'rating': 'Puan', 'comment': 'Yorum (opsiyonel)'}
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Satıcıyla deneyiminizi birkaç cümleyle anlatın…',
                }
            ),
        }
