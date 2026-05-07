from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Book
from .forms import BookForm

# Tüm satılık kitapları listele (Ana Sayfa)
def book_list(request):
    books = Book.objects.filter(is_sold=False).order_by('-created_at')
    return render(request, 'books/book_list.html', {'books': books})

# Kitap detay sayfası
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'books/book_detail.html', {'book': book})

# Yeni kitap ilanı oluştur (Sadece giriş yapmış kullanıcılar)
@login_required
def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES) # Resimler için request.FILES şart!
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user # İlanı yükleyen kişi o anki kullanıcıdır
            book.save()
            return redirect('book_list')
    else:
        form = BookForm()
    return render(request, 'books/book_form.html', {'form': form})