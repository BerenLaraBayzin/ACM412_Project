from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from books.models import Order
from .forms import UserRegisterForm


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
        .select_related('book')
        .order_by('-ordered_at')
    )
    return render(
        request,
        'users/profile.html',
        {'listings': listings, 'purchases': purchases},
    )