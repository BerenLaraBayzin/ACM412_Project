from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from books.models import Profile


class ProfileEditForm(forms.Form):
    """Kullanıcı + profil bilgilerini tek formda düzenler."""
    first_name = forms.CharField(max_length=30, required=False, label='Ad')
    last_name = forms.CharField(max_length=30, required=False, label='Soyad')
    email = forms.EmailField(required=True, label='E-posta')
    phone = forms.CharField(max_length=20, required=False, label='Telefon')
    city = forms.CharField(max_length=80, required=False, label='Şehir')
    address = forms.CharField(
        required=False, label='Varsayılan teslimat adresi',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            css = 'form-control'
            f.widget.attrs['class'] = css

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('Bu e-posta başka bir hesapta kayıtlı.')
        return email

    def save(self):
        u = self.user
        u.first_name = self.cleaned_data['first_name']
        u.last_name = self.cleaned_data['last_name']
        u.email = self.cleaned_data['email']
        u.save()
        Profile.objects.update_or_create(
            user=u,
            defaults={
                'phone': self.cleaned_data.get('phone', ''),
                'city': self.cleaned_data.get('city', ''),
                'address': self.cleaned_data.get('address', ''),
            },
        )
        return u


class UserRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label='Ad')
    last_name = forms.CharField(max_length=30, required=True, label='Soyad')
    email = forms.EmailField(required=True, label='E-posta')
    phone = forms.CharField(max_length=20, required=False, label='Telefon (opsiyonel)')
    city = forms.CharField(max_length=80, required=False, label='Şehir (opsiyonel)')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'first_name': 'Adınız',
            'last_name': 'Soyadınız',
            'username': 'kullaniciadi',
            'email': 'ornek@eposta.com',
            'phone': '05XX XXX XX XX',
            'city': 'İstanbul',
        }
        for name in self.fields:
            self.fields[name].widget.attrs['class'] = 'form-control'
            if name in placeholders:
                self.fields[name].widget.attrs.setdefault('placeholder', placeholders[name])

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Bu e-posta zaten kayıtlı.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    'phone': self.cleaned_data.get('phone', ''),
                    'city': self.cleaned_data.get('city', ''),
                },
            )
        return user
