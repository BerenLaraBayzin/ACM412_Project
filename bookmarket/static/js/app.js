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

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('.btn-favorite[data-toggle-url]');
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
      btn.classList.toggle('is-favorited', data.favorited);
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
