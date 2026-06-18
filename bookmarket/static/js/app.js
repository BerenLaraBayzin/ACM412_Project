(function () {
  const root = document.documentElement;
  const STORAGE_KEY = 'bm-theme';

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
      toggle.textContent = theme === 'dark' ? '☀' : '☾';
      toggle.setAttribute('aria-label', theme === 'dark' ? 'Açık tema' : 'Koyu tema');
    }
  }

  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    applyTheme(saved);
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    applyTheme('dark');
  } else {
    applyTheme('light');
  }

  document.addEventListener('click', function (e) {
    const t = e.target.closest('.theme-toggle');
    if (!t) return;
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(STORAGE_KEY, next);
  });

  // Mobile nav toggle
  document.addEventListener('click', function (e) {
    const t = e.target.closest('[data-toggle-nav]');
    if (!t) return;
    const links = document.querySelector('.nav-links');
    if (links) links.classList.toggle('mobile-open');
  });

  // Alert close
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-close-alert]');
    if (!btn) return;
    const alert = btn.closest('.alert');
    if (!alert) return;
    alert.classList.add('is-hiding');
    setTimeout(() => alert.remove(), 250);
  });

  // Auto-dismiss success alerts after 4s
  document.querySelectorAll('.alert-success').forEach(function (a) {
    setTimeout(() => {
      a.classList.add('is-hiding');
      setTimeout(() => a.remove(), 250);
    }, 4500);
  });

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('.fav-btn[data-toggle-url], .fav-detail[data-toggle-url]');
    if (!btn) return;
    e.preventDefault();
    if (btn.dataset.busy === '1') return;
    btn.dataset.busy = '1';
    try {
      const res = await fetch(btn.dataset.toggleUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (res.status === 403 || res.status === 401) {
        window.location.href = btn.dataset.loginUrl || '/users/login/';
        return;
      }
      if (!res.ok) throw new Error('favorite toggle failed');
      const data = await res.json();
      btn.classList.toggle('is-on', data.favorited);
      const countEl = btn.querySelector('.count');
      if (countEl) countEl.textContent = data.favorite_count;
      const heart = btn.querySelector('.heart');
      if (heart) {
        heart.textContent = data.favorited ? '♥' : '♡';
      }
    } catch (err) {
      console.error(err);
    } finally {
      btn.dataset.busy = '0';
    }
  });

  // ISBN lookup (Open Library)
  const isbnBtn = document.getElementById('isbn-fetch');
  const isbnInput = document.getElementById('isbn');
  const isbnResult = document.getElementById('isbn-result');
  const coverUrlField = document.getElementById('cover_url');
  if (isbnBtn && isbnInput && isbnResult) {
    isbnBtn.addEventListener('click', async function () {
      const isbn = (isbnInput.value || '').replace(/[\s-]/g, '');
      if (!/^\d{10}(\d{3})?$/.test(isbn)) {
        isbnResult.className = 'isbn-result is-shown is-error';
        isbnResult.textContent = '10 veya 13 haneli ISBN girin.';
        return;
      }
      isbnResult.className = 'isbn-result is-shown';
      isbnResult.textContent = 'Aranıyor…';
      isbnBtn.disabled = true;
      try {
        const res = await fetch('/isbn-lookup/?isbn=' + encodeURIComponent(isbn), {
          credentials: 'same-origin',
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || 'lookup_failed');
        }
        const data = await res.json();
        isbnResult.className = 'isbn-result is-shown';
        isbnResult.innerHTML =
          (data.cover_url ? '<img src="' + data.cover_url + '" alt="">' : '') +
          '<div class="meta"><strong></strong><br><span></span></div>';
        isbnResult.querySelector('strong').textContent = data.title || '(başlık yok)';
        isbnResult.querySelector('span').textContent = data.author || '';
        // Form alanlarını doldur
        const titleField = document.querySelector('#book-form input[name="title"]');
        const authorField = document.querySelector('#book-form input[name="author"]');
        if (titleField && data.title) titleField.value = data.title;
        if (authorField && data.author) authorField.value = data.author;
        if (coverUrlField && data.cover_url) coverUrlField.value = data.cover_url;
      } catch (err) {
        isbnResult.className = 'isbn-result is-shown is-error';
        const msg = {
          invalid_isbn: 'Geçersiz ISBN biçimi.',
          not_found: 'Bu ISBN için kayıt bulunamadı.',
          api_unreachable: 'Open Library yanıt vermedi, sonra dene.',
        }[err.message] || 'Bir hata oluştu.';
        isbnResult.textContent = msg;
      } finally {
        isbnBtn.disabled = false;
      }
    });
  }

  // Checkout — ödeme yöntemine göre kart alanlarını göster/gizle
  const payOptions = document.querySelector('[data-pay-options]');
  const cardFields = document.querySelector('[data-card-fields]');
  if (payOptions && cardFields) {
    const sync = function () {
      const sel = payOptions.querySelector('input[name="payment_method"]:checked');
      const isCard = !sel || sel.value === 'card';
      cardFields.style.display = isCard ? '' : 'none';
    };
    payOptions.addEventListener('change', sync);
    sync();
  }

  // Kart numarasını 4'lü gruplara ayır (görsel)
  const cardNumber = document.getElementById('id_card_number');
  if (cardNumber) {
    cardNumber.addEventListener('input', function () {
      let v = cardNumber.value.replace(/\D/g, '').slice(0, 19);
      cardNumber.value = v.replace(/(.{4})/g, '$1 ').trim();
    });
  }

  // Son kullanma tarihine otomatik "/" ekle
  const cardExpiry = document.getElementById('id_card_expiry');
  if (cardExpiry) {
    cardExpiry.addEventListener('input', function () {
      let v = cardExpiry.value.replace(/\D/g, '').slice(0, 4);
      if (v.length >= 3) v = v.slice(0, 2) + '/' + v.slice(2);
      cardExpiry.value = v;
    });
  }

  const form = document.querySelector('form[data-ajax-message]');
  if (form) {
    const list = document.querySelector('[data-thread-messages]');
    const me = form.dataset.username;
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const textarea = form.querySelector('textarea[name="body"]');
      const body = (textarea.value || '').trim();
      if (!body) return;
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      try {
        const data = new FormData();
        data.append('body', body);
        const res = await fetch(form.action, {
          method: 'POST',
          body: data,
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        if (!res.ok) throw new Error('send failed');
        const msg = await res.json();
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble mine';
        bubble.innerHTML =
          '<div class="body"></div><div class="meta"></div>';
        bubble.querySelector('.body').textContent = msg.body;
        bubble.querySelector('.meta').textContent = msg.sender + ' • ' + msg.sent_at;
        list.appendChild(bubble);
        list.scrollTop = list.scrollHeight;
        textarea.value = '';
      } catch (err) {
        console.error(err);
        alert('Mesaj gönderilemedi.');
      } finally {
        submitBtn.disabled = false;
      }
    });
  }
})();
