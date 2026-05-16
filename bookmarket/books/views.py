from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BookForm, MessageForm, OrderPurchaseForm
from .models import Book, Category, Message, Order


def _filter_querystring(request, exclude=('page',)):
    q = request.GET.copy()
    for key in exclude:
        q.pop(key, None)
    s = q.urlencode()
    return f'&{s}' if s else ''


def book_list(request):
    qs = (
        Book.objects.filter(is_sold=False)
        .select_related('category', 'seller')
        .order_by('-created_at')
    )

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

    paginator = Paginator(qs, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    user_favorite_ids = set()
    if request.user.is_authenticated:
        user_favorite_ids = set(
            request.user.favorite_books.filter(
                pk__in=[b.pk for b in page_obj]
            ).values_list('pk', flat=True)
        )

    context = {
        'page_obj': page_obj,
        'books': page_obj,
        'categories': Category.objects.all().order_by('name'),
        'filter_q': q,
        'filter_category': category_id or '',
        'filter_condition': condition or '',
        'filter_min_price': request.GET.get('min_price', ''),
        'filter_max_price': request.GET.get('max_price', ''),
        'querystring': _filter_querystring(request),
        'user_favorite_ids': user_favorite_ids,
    }
    return render(request, 'books/book_list.html', context)


def book_detail(request, pk):
    book = get_object_or_404(
        Book.objects.select_related('category', 'seller'),
        pk=pk,
    )
    context = {
        'book': book,
        'favorite_count': book.favorited_by.count(),
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
@require_POST
def favorite_toggle(request, pk):
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
    qs = (
        request.user.favorite_books
        .select_related('category', 'seller')
        .order_by('-created_at')
    )
    return render(request, 'books/favorites_list.html', {'books': qs})


@login_required
@require_POST
def message_send_ajax(request, book_pk, user_pk):
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
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.seller = request.user
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
