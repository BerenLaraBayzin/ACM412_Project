"""HTML view'ları: kitap CRUD, sipariş akışı, mesajlaşma, favoriler ve ISBN lookup.

REST API uçları için bkz: ``books.api_views``.
"""
from collections import OrderedDict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookForm, MessageForm, OrderPurchaseForm, ReviewForm
from .models import Book, Category, Message, Order, Review


# Sıralama seçenekleri: arayüzdeki değer -> (etiket, ORM order_by ifadesi)
SORT_OPTIONS = {
    'new': ('En yeni', '-created_at'),
    'price_asc': ('Fiyat (artan)', 'price'),
    'price_desc': ('Fiyat (azalan)', '-price'),
    'popular': ('En çok beğenilen', '-fav_count'),
}


def seller_rating(user):
    """Bir satıcının aldığı değerlendirmelerin ortalaması ve sayısı.

    Tek bir aggregate sorgusuyla hesaplanır. Döndürülen ``avg`` None olabilir
    (hiç değerlendirme yoksa); şablon tarafında ``default`` ile ele alınır.
    """
    agg = user.received_reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    return {'avg': agg['avg'], 'count': agg['count']}


def _mark_new_flag(books):
    """Son 7 gün içinde eklenen kitaplara ``is_new=True`` bayrağı atar."""
    cutoff = timezone.now() - timedelta(days=7)
    for b in books:
        b.is_new = b.created_at >= cutoff
    return books


def _filter_querystring(request, exclude=('page',)):
    q = request.GET.copy()
    for key in exclude:
        q.pop(key, None)
    s = q.urlencode()
    return f'&{s}' if s else ''


def book_list(request):
    """Anasayfa + arama/filtre sonuçları.

    Filtre yokken (anasayfa) editör seçimi, kategori rafları ve istatistikler;
    filtre varken sayfalanmış ürün ızgarası gösterilir.
    """
    qs = (
        Book.objects.filter(is_sold=False)
        .select_related('category', 'seller')
        .annotate(fav_count=Count('favorited_by'))
    )

    sort = request.GET.get('sort')
    if sort not in SORT_OPTIONS:
        sort = 'new'
    qs = qs.order_by(SORT_OPTIONS[sort][1], '-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q))

    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    condition = request.GET.get('condition')
    if condition in dict(Book.CONDITION_CHOICES):
        qs = qs.filter(condition=condition)

    try:
        min_price = request.GET.get('min_price')
        if min_price not in (None, ''):
            qs = qs.filter(price__gte=min_price)
    except (TypeError, ValueError):
        pass

    try:
        max_price = request.GET.get('max_price')
        if max_price not in (None, ''):
            qs = qs.filter(price__lte=max_price)
    except (TypeError, ValueError):
        pass

    has_filters = any([q, category_id, condition, request.GET.get('min_price'),
                       request.GET.get('max_price'), request.GET.get('sort')])
    show_home_widgets = not has_filters

    deal_book = None
    featured_books = []
    newest_books = []
    category_cards = []
    category_shelves = []
    all_widget_pks = []

    if show_home_widgets:
        deal_book = (
            Book.objects.filter(is_sold=False, condition__in=['used', 'good'])
            .select_related('category', 'seller')
            .order_by('-price')
            .first()
        )
        featured_books = list(
            Book.objects.filter(is_sold=False)
            .select_related('category', 'seller')
            .annotate(fav_count=Count('favorited_by'))
            .order_by('-fav_count', '-created_at')[:6]
        )
        newest_books = list(
            Book.objects.filter(is_sold=False)
            .select_related('category', 'seller')
            .order_by('-created_at')[:6]
        )
        category_cards = _build_category_cards()
        category_shelves = _build_category_shelves(limit_per_cat=4)
        all_widget_pks = (
            [deal_book.pk] if deal_book else []
        ) + [b.pk for b in featured_books] + [b.pk for b in newest_books] + [
            b.pk for shelf in category_shelves for b in shelf['books']
        ]

    page_obj = None
    if not show_home_widgets:
        paginator = Paginator(qs, 12)
        page_obj = paginator.get_page(request.GET.get('page'))

    user_favorite_ids = set()
    if request.user.is_authenticated:
        candidate_pks = list(all_widget_pks)
        if page_obj is not None:
            candidate_pks += [b.pk for b in page_obj]
        if candidate_pks:
            user_favorite_ids = set(
                request.user.favorite_books.filter(pk__in=candidate_pks)
                .values_list('pk', flat=True)
            )

    nav_categories = list(Category.objects.all().order_by('name'))[:8]
    total_count = Book.objects.filter(is_sold=False).count()
    seller_count = (
        Book.objects.filter(is_sold=False)
        .values('seller_id').distinct().count()
    )

    context = {
        'page_obj': page_obj,
        'books': page_obj,
        'show_home_widgets': show_home_widgets,
        'deal_book': deal_book,
        'featured_books': featured_books,
        'newest_books': newest_books,
        'category_cards': category_cards,
        'category_shelves': category_shelves,
        'nav_categories': nav_categories,
        'categories': Category.objects.all().order_by('name'),
        'filter_q': q,
        'filter_category': category_id or '',
        'filter_condition': condition or '',
        'filter_min_price': request.GET.get('min_price', ''),
        'filter_max_price': request.GET.get('max_price', ''),
        'filter_sort': sort,
        'sort_options': [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        'querystring': _filter_querystring(request),
        'user_favorite_ids': user_favorite_ids,
        'total_count': total_count,
        'seller_count': seller_count,
    }
    return render(request, 'books/book_list.html', context)


CATEGORY_ICONS = {
    'roman':           '📚',
    'felsefe':         '💭',
    'bilim-teknoloji': '🔬',
    'tarih':           '🏛',
    'siir':            '🪶',
    'polisiye':        '🕵',
    'cocuk-genc':      '🧸',
    'kisisel-gelisim': '🌱',
}


def _build_category_cards():
    cats = (
        Category.objects.annotate(
            book_count=Count('books', filter=Q(books__is_sold=False)),
        ).order_by('-book_count')
    )
    cards = []
    for c in cats:
        cards.append({
            'pk': c.pk,
            'name': c.name,
            'book_count': c.book_count,
            'icon': CATEGORY_ICONS.get(c.slug, '📖'),
        })
    return cards


def _build_category_shelves(limit_per_cat=4):
    shelves = []
    for c in Category.objects.all().order_by('name'):
        books = list(
            Book.objects.filter(is_sold=False, category=c)
            .select_related('category', 'seller')
            .order_by('-created_at')[:limit_per_cat]
        )
        if len(books) >= 2:
            shelves.append({'pk': c.pk, 'name': c.name, 'books': books})
    return shelves[:4]


def book_detail(request, pk):
    """Kitap detay sayfası. Kullanıcının izinlerine göre satın al/yaz/düzenle butonlarını koşullandırır."""
    book = get_object_or_404(
        Book.objects.select_related('category', 'seller'),
        pk=pk,
    )
    context = {
        'book': book,
        'favorite_count': book.favorited_by.count(),
        'seller_rating': seller_rating(book.seller),
    }
    user = request.user
    if user.is_authenticated:
        has_order = Order.objects.filter(book=book).exists()
        context['can_buy'] = (
            not book.is_sold
            and not has_order
            and book.seller_id != user.id
        )
        context['can_message'] = (
            not book.is_sold and book.seller_id != user.id
        )
        context['is_favorited'] = book.favorited_by.filter(pk=user.pk).exists()
        if context['can_message']:
            has_thread = Message.objects.filter(
                book=book,
            ).filter(
                Q(sender=user, receiver=book.seller)
                | Q(sender=book.seller, receiver=user),
            ).exists()
            context['message_thread_exists'] = has_thread
    if book.is_sold:
        context['sale'] = (
            Order.objects.filter(book=book).select_related('buyer').first()
        )
    return render(request, 'books/book_detail.html', context)


@login_required
def isbn_lookup(request):
    """Open Library Books API ile ISBN'den başlık, yazar ve kapak URL'si çek.

    Endpoint: GET /isbn-lookup/?isbn=9780451524935
    Kullanılan API: https://openlibrary.org/dev/docs/api/books
    Sadece giriş yapmış kullanıcılar; rate-limit yok (Open Library açık).
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    isbn = (request.GET.get('isbn') or '').strip().replace('-', '').replace(' ', '')
    if not isbn or not isbn.isdigit() or len(isbn) not in (10, 13):
        return JsonResponse({'error': 'invalid_isbn'}, status=400)

    api_url = (
        'https://openlibrary.org/api/books?bibkeys=ISBN:'
        + urllib.parse.quote(isbn)
        + '&jscmd=data&format=json'
    )
    try:
        req = urllib.request.Request(
            api_url, headers={'User-Agent': 'BookMarket/1.0'},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return JsonResponse({'error': 'api_unreachable'}, status=502)

    key = f'ISBN:{isbn}'
    info = data.get(key)
    if not info:
        return JsonResponse({'error': 'not_found'}, status=404)

    cover_url = ''
    cover = info.get('cover') or {}
    cover_url = cover.get('large') or cover.get('medium') or cover.get('small') or ''
    if not cover_url:
        cover_url = f'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg'

    return JsonResponse({
        'title': info.get('title', ''),
        'author': ', '.join(a.get('name', '') for a in info.get('authors', [])),
        'cover_url': cover_url,
        'publish_date': info.get('publish_date', ''),
    })


@login_required
@require_POST
def favorite_toggle(request, pk):
    """AJAX endpoint: bir kitabı kullanıcının favorilerine ekler/çıkarır.

    POST `/book/<pk>/favori/` → JSON `{favorited: bool, favorite_count: int}`.
    M2M `Book.favorited_by` ilişkisini günceller.
    """
    book = get_object_or_404(Book, pk=pk)
    user = request.user
    if book.favorited_by.filter(pk=user.pk).exists():
        book.favorited_by.remove(user)
        favorited = False
    else:
        book.favorited_by.add(user)
        favorited = True
    return JsonResponse({
        'favorited': favorited,
        'favorite_count': book.favorited_by.count(),
    })


@login_required
def favorites_list(request):
    qs = list(
        request.user.favorite_books
        .select_related('category', 'seller')
        .order_by('-created_at')
    )
    _mark_new_flag(qs)
    return render(request, 'books/favorites_list.html', {
        'books': qs,
        'user_favorite_ids': {b.pk for b in qs},
    })


@login_required
@require_POST
def message_send_ajax(request, book_pk, user_pk):
    """AJAX endpoint: mesaj iş parçacığında canlı yanıt gönderir."""
    book = get_object_or_404(Book, pk=book_pk)
    with_user = get_object_or_404(get_user_model(), pk=user_pk)
    if not _thread_allowed(request.user, book, with_user) and not (
        not book.is_sold and book.seller_id == with_user.id
    ):
        return JsonResponse({'error': 'forbidden'}, status=403)
    body = (request.POST.get('body') or '').strip()
    if not body:
        return JsonResponse({'error': 'empty'}, status=400)
    msg = Message.objects.create(
        sender=request.user, receiver=with_user, book=book, body=body,
    )
    return JsonResponse({
        'id': msg.id,
        'body': msg.body,
        'sender': msg.sender.username,
        'sent_at': msg.sent_at.strftime('%d.%m.%Y %H:%M'),
    })


@login_required
def book_create(request):
    """Yeni kitap ilanı oluşturma.

    Görsel iki kaynaktan gelebilir:
      1) Form'da yüklenmiş `image` dosyası (öncelikli).
      2) Gizli `cover_url` alanı — Open Library ISBN lookup sonucu,
         JS tarafından doldurulur; bu URL sunucuda indirilip ImageField'a kaydedilir.
    """
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
            cover_url = (request.POST.get('cover_url') or '').strip()
            if cover_url and not request.FILES.get('image'):
                _attach_remote_cover(book, cover_url)
            book.save()
            messages.success(request, 'İlanınız yayınlandı.')
            return redirect('book_list')
    else:
        form = BookForm()
    return render(
        request,
        'books/book_form.html',
        {'form': form, 'form_title': 'Yeni kitap ilanı'},
    )


def _attach_remote_cover(book, url):
    """Open Library kapak URL'sini sunucuya indirip Book.image alanına ata."""
    import urllib.error
    import urllib.request
    from django.core.files.base import ContentFile
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BookMarket/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        if len(data) < 500:
            return  # boş/eksik kapak — pas geç
        book.image.save(f'isbn_{book.title[:30]}.jpg', ContentFile(data), save=False)
    except (urllib.error.URLError, TimeoutError):
        return


@login_required
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if book.seller_id != request.user.id:
        return HttpResponseForbidden('Bu ilanı yalnızca ilan sahibi düzenleyebilir.')
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'İlan güncellendi.')
            return redirect('book_detail', pk=book.pk)
    else:
        form = BookForm(instance=book)
    return render(
        request,
        'books/book_form.html',
        {'form': form, 'form_title': 'İlanı düzenle', 'book': book},
    )


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if book.seller_id != request.user.id:
        return HttpResponseForbidden('Bu ilanı yalnızca ilan sahibi silebilir.')
    if request.method == 'POST':
        book.delete()
        messages.success(request, 'İlan silindi.')
        return redirect('book_list')
    return render(request, 'books/book_confirm_delete.html', {'book': book})


@login_required
def order_create(request, pk):
    """Satın alma akışı.

    Yarış-koşulu güvenliği: ``transaction.atomic`` içinde
    ``Book.objects.select_for_update()`` ile kilitlenir; iki paralel satın alma
    isteğinden yalnızca biri başarılı olur.
    """
    book = get_object_or_404(
        Book.objects.select_related('seller'),
        pk=pk,
    )
    if book.seller_id == request.user.id:
        return HttpResponseForbidden('Kendi ilanınızı satın alamazsınız.')
    if book.is_sold or Order.objects.filter(book=book).exists():
        messages.error(request, 'Bu kitap satılmış veya satışta değil.')
        return redirect('book_detail', pk=book.pk)

    if request.method == 'POST':
        form = OrderPurchaseForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    locked = Book.objects.select_for_update().get(pk=book.pk)
                    if locked.is_sold or Order.objects.filter(book=locked).exists():
                        messages.error(request, 'Bu kitap az önce satıldı.')
                        return redirect('book_detail', pk=book.pk)
                    if locked.seller_id == request.user.id:
                        return HttpResponseForbidden(
                            'Kendi ilanınızı satın alamazsınız.'
                        )
                    order = form.save(commit=False)
                    order.buyer = request.user
                    order.book = locked
                    order.save()
                    locked.is_sold = True
                    locked.save(update_fields=['is_sold'])
            except Book.DoesNotExist:
                messages.error(request, 'İlan bulunamadı.')
                return redirect('book_list')
            messages.success(
                request,
                'Siparişiniz alındı. Satıcı teslimat için sizinle iletişime geçebilir.',
            )
            return redirect('book_detail', pk=book.pk)
    else:
        form = OrderPurchaseForm()
    return render(
        request,
        'books/order_form.html',
        {'form': form, 'book': book},
    )


def _thread_allowed(user, book, with_user):
    if user.id == with_user.id:
        return False
    return Message.objects.filter(book=book).filter(
        Q(sender=user, receiver=with_user)
        | Q(sender=with_user, receiver=user),
    ).exists()


@login_required
def message_list(request):
    msgs = (
        Message.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user),
        )
        .select_related('book', 'sender', 'receiver')
        .order_by('-sent_at')
    )
    threads = OrderedDict()
    for m in msgs:
        other = m.receiver if m.sender_id == request.user.id else m.sender
        key = (m.book_id, other.id)
        if key not in threads:
            threads[key] = {
                'book': m.book,
                'other': other,
                'last': m,
            }
    return render(
        request,
        'books/message_list.html',
        {'threads': threads.values()},
    )


@login_required
def message_compose(request, book_pk):
    book = get_object_or_404(
        Book.objects.select_related('seller'),
        pk=book_pk,
    )
    if book.seller_id == request.user.id:
        return HttpResponseForbidden('Kendi ilanınıza mesaj gönderemezsiniz.')
    if book.is_sold:
        messages.error(request, 'Satılmış ilanlara yeni mesaj gönderilemez.')
        return redirect('book_detail', pk=book.pk)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = book.seller
            msg.book = book
            msg.save()
            messages.success(request, 'Mesajınız gönderildi.')
            return redirect(
                'message_thread',
                book_pk=book.pk,
                user_pk=book.seller_id,
            )
    else:
        form = MessageForm()
    return render(
        request,
        'books/message_compose.html',
        {'form': form, 'book': book},
    )


@login_required
def message_thread(request, book_pk, user_pk):
    book = get_object_or_404(Book, pk=book_pk)
    with_user = get_object_or_404(
        get_user_model(),
        pk=user_pk,
    )
    if not _thread_allowed(request.user, book, with_user):
        messages.error(request, 'Bu konuşmayı görüntüleme yetkiniz yok.')
        return redirect('message_list')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.receiver = with_user
            msg.book = book
            msg.save()
            messages.success(request, 'Mesaj gönderildi.')
            return redirect('message_thread', book_pk=book.pk, user_pk=user_pk)
    else:
        form = MessageForm()

    thread_messages = (
        Message.objects.filter(book=book)
        .filter(
            Q(sender=request.user, receiver=with_user)
            | Q(sender=with_user, receiver=request.user),
        )
        .select_related('sender', 'receiver')
        .order_by('sent_at')
    )
    return render(
        request,
        'books/message_thread.html',
        {
            'book': book,
            'with_user': with_user,
            'thread_messages': thread_messages,
            'form': form,
        },
    )


def seller_profile(request, username):
    """Herkese açık satıcı vitrini.

    Satıcının aktif ilanları, satış/ilan istatistikleri, ortalama puanı ve
    aldığı son değerlendirmeler gösterilir.
    """
    seller = get_object_or_404(get_user_model(), username=username)

    listings = list(
        seller.books.filter(is_sold=False)
        .select_related('category', 'seller')
        .annotate(fav_count=Count('favorited_by'))
        .order_by('-created_at')
    )
    _mark_new_flag(listings)

    reviews = list(
        seller.received_reviews
        .select_related('reviewer', 'order__book')
        .order_by('-created_at')[:20]
    )

    user_favorite_ids = set()
    if request.user.is_authenticated and listings:
        user_favorite_ids = set(
            request.user.favorite_books
            .filter(pk__in=[b.pk for b in listings])
            .values_list('pk', flat=True)
        )

    context = {
        'seller': seller,
        'listings': listings,
        'reviews': reviews,
        'rating': seller_rating(seller),
        'active_count': len(listings),
        'sold_count': seller.books.filter(is_sold=True).count(),
        'user_favorite_ids': user_favorite_ids,
    }
    return render(request, 'books/seller_profile.html', context)


@login_required
def review_create(request, order_pk):
    """Sipariş sahibinin, satıcıya değerlendirme bırakması.

    Yalnızca siparişin alıcısı; her sipariş için tek değerlendirme. Mevcutsa
    formu düzenleme moduna geçer.
    """
    order = get_object_or_404(
        Order.objects.select_related('book', 'book__seller', 'buyer'),
        pk=order_pk,
    )
    if order.buyer_id != request.user.id:
        return HttpResponseForbidden('Yalnızca siparişin sahibi değerlendirme yapabilir.')

    existing = Review.objects.filter(order=order).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.order = order
            review.reviewer = request.user
            review.seller = order.book.seller
            review.save()
            messages.success(request, 'Değerlendirmeniz kaydedildi. Teşekkürler!')
            return redirect('seller_profile', username=order.book.seller.username)
    else:
        form = ReviewForm(instance=existing)

    return render(
        request,
        'books/review_form.html',
        {'form': form, 'order': order, 'editing': existing is not None},
    )
