async function request(path, opts = {}) {
  const { method = 'GET', body, form } = opts;
  const init = { method, credentials: 'include', headers: { ...(opts.headers || {}) } };
  if (form) init.body = form;
  else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, init);
  } catch (e) {
    throw new Error('Network error — is the server running?');
  }
  const onAuthPage = /\/(login|register)\.html$/.test(location.pathname);
  if (res.status === 401 && !onAuthPage) {
    location.href = '/login.html';
    throw new Error('Not logged in');
  }
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    if (data && data.detail) {
      msg = typeof data.detail === 'string'
        ? data.detail
        : data.detail.map(d => `${(d.loc || []).join('.')}: ${d.msg}`).join('; ');
    }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function toast(message, isError = false) {
  document.querySelectorAll('.toast').forEach(t => t.remove());
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function setBusy(btn, busy, label = 'Working…') {
  if (busy) {
    btn.dataset.label = btn.textContent;
    btn.disabled = true;
    btn.textContent = label;
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.label || btn.textContent;
  }
}
