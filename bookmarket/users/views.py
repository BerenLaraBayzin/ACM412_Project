from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from books.models import Order, Profile
from .forms import ProfileEditForm, UserRegisterForm


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(
                request,
                f'Hesabınız oluşturuldu, {username}! Giriş yapabilirsiniz.',
            )
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    listings = request.user.books.select_related('category').order_by('-created_at')
    purchases = (
        Order.objects.filter(buyer=request.user)
        .select_related('book', 'book__seller', 'review')
        .order_by('-ordered_at')
    )
    sales = (
        Order.objects.filter(book__seller=request.user)
        .select_related('book', 'buyer')
        .order_by('-ordered_at')
    )
    return render(
        request,
        'users/profile.html',
        {'listings': listings, 'purchases': purchases, 'sales': sales},
    )


@login_required
def profile_edit(request):
    profile = Profile.objects.filter(user=request.user).first()
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profilin güncellendi.')
            return redirect('profile')
    else:
        form = ProfileEditForm(user=request.user, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': profile.phone if profile else '',
            'city': profile.city if profile else '',
            'address': profile.address if profile else '',
        })
    return render(request, 'users/profile_edit.html', {'form': form})