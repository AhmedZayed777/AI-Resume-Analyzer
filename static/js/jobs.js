let me = null;

function currentFilters() {
  return {
    q: document.getElementById('q').value.trim(),
    location: document.getElementById('location').value.trim(),
    skill: document.getElementById('skill').value.trim(),
  };
}

async function loadJobs(filters = {}) {
  const box = document.getElementById('jobs');
  box.innerHTML = '<div class="empty">Loading…</div>';
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
  try {
    const jobs = await request('/api/jobs' + (params.toString() ? `?${params}` : ''));
    if (!jobs.length) {
      box.innerHTML = '<div class="empty">No jobs match your search. Try different keywords or reset the filters.</div>';
      return;
    }
    box.innerHTML = jobs.map(j => `
      <div class="card">
        <div class="list-item">
          <h3>${escapeHtml(j.title)}</h3>
          <span class="muted">${j.min_years_experience > 0 ? `${j.min_years_experience}+ yrs` : 'No exp. req.'}</span>
        </div>
        <div class="muted">${escapeHtml(j.company || '—')} · ${escapeHtml(j.location || '—')}</div>
        <p class="muted">${escapeHtml(j.description)}</p>
        <div class="chips">${j.required_skills.map(s => `<span class="chip tech">${escapeHtml(s)}</span>`).join('')}</div>
        ${me && me.id === j.created_by ? `
          <div style="margin-top:.7rem; display:flex; gap:.5rem">
            <button class="btn btn-sm" data-edit="${j.id}">Edit</button>
            <button class="btn btn-danger btn-sm" data-del="${j.id}">Delete</button>
          </div>` : ''}
      </div>`).join('');
    box.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => openModal(Number(b.dataset.edit)));
    box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => deleteJob(Number(b.dataset.del)));
  } catch (e) {
    box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}

async function openModal(jobId = null) {
  const modal = document.getElementById('job-modal');
  const form = document.getElementById('job-form');
  document.getElementById('error-box').style.display = 'none';
  form.reset();
  document.getElementById('job-id').value = '';
  document.getElementById('modal-title').textContent = jobId ? 'Edit job' : 'Add job';
  if (jobId) {
    const j = await request(`/api/jobs/${jobId}`);
    document.getElementById('job-id').value = j.id;
    form.title.value = j.title;
    form.company.value = j.company;
    document.getElementById('jlocation').value = j.location;
    form.description.value = j.description;
    document.getElementById('skills').value = j.required_skills.join(', ');
    form.years.value = j.min_years_experience;
  }
  modal.style.display = 'flex';
}

async function deleteJob(id) {
  if (!confirm('Delete this job?')) return;
  try {
    await request(`/api/jobs/${id}`, { method: 'DELETE' });
    toast('Job deleted');
    loadJobs(currentFilters());
  } catch (e) {
    toast(e.message, true);
  }
}

window.initPage = async () => {
  me = await getMe();
  if (me) document.getElementById('new-job-btn').style.display = 'inline-block';
  await loadJobs();

  document.getElementById('search-form').onsubmit = (e) => { e.preventDefault(); loadJobs(currentFilters()); };
  document.getElementById('reset-btn').onclick = () => {
    document.getElementById('search-form').reset();
    loadJobs();
  };
  document.getElementById('new-job-btn').onclick = () => openModal();
  document.getElementById('cancel-btn').onclick = () => { document.getElementById('job-modal').style.display = 'none'; };

  document.getElementById('job-form').onsubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const id = document.getElementById('job-id').value;
    const payload = {
      title: form.title.value,
      company: form.company.value,
      location: document.getElementById('jlocation').value,
      description: form.description.value,
      required_skills: document.getElementById('skills').value.split(',').map(s => s.trim()).filter(Boolean),
      min_years_experience: Number(form.years.value || 0),
    };
    const btn = form.querySelector('button[type=submit]');
    setBusy(btn, true, 'Saving…');
    try {
      if (id) await request(`/api/jobs/${id}`, { method: 'PUT', body: payload });
      else await request('/api/jobs', { method: 'POST', body: payload });
      document.getElementById('job-modal').style.display = 'none';
      toast(id ? 'Job updated' : 'Job created');
      loadJobs(currentFilters());
    } catch (err) {
      showError(err.message);
    } finally {
      setBusy(btn, false);
    }
  };
};
