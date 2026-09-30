let cachedMe;

async function getMe(force = false) {
  if (!force && cachedMe !== undefined) return cachedMe;
  try {
    cachedMe = await request('/api/auth/me');
  } catch (e) {
    cachedMe = null;
  }
  return cachedMe;
}

async function renderAuthArea() {
  const area = document.getElementById('auth-area');
  if (!area) return;
  const me = await getMe();
  if (me) {
    area.innerHTML = `<span class="muted">Hi, ${escapeHtml(me.full_name || me.email)}</span>
      <button class="btn btn-ghost btn-sm" id="logout-btn">Log out</button>`;
    document.getElementById('logout-btn').onclick = async () => {
      try { await request('/api/auth/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
      cachedMe = undefined;
      location.href = '/login.html';
    };
  } else {
    area.innerHTML = `<a href="/login.html">Log in</a>
      <a class="btn btn-primary btn-sm" href="/register.html">Sign up</a>`;
  }
}

function showError(message) {
  const box = document.getElementById('error-box');
  if (box) {
    box.textContent = message;
    box.style.display = 'block';
  } else {
    toast(message, true);
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      const btn = loginForm.querySelector('button[type=submit]');
      setBusy(btn, true, 'Logging in…');
      try {
        await request('/api/auth/login', {
          method: 'POST',
          body: { email: loginForm.email.value, password: loginForm.password.value },
        });
        location.href = '/index.html';
      } catch (err) {
        showError(err.message);
        setBusy(btn, false);
      }
    };
  }
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.onsubmit = async (e) => {
      e.preventDefault();
      if (registerForm.password.value !== registerForm.confirm.value) {
        showError('Passwords do not match.');
        return;
      }
      const btn = registerForm.querySelector('button[type=submit]');
      setBusy(btn, true, 'Creating account…');
      try {
        await request('/api/auth/register', {
          method: 'POST',
          body: {
            email: registerForm.email.value,
            password: registerForm.password.value,
            full_name: registerForm.full_name.value,
          },
        });
        location.href = '/index.html';
      } catch (err) {
        showError(err.message);
        setBusy(btn, false);
      }
    };
  }
  await renderAuthArea();
  if (window.initPage) await window.initPage();
});
