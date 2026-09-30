let currentResumeId = null;

function chips(el, items, cls = '') {
  el.innerHTML = (items || []).map(s => `<span class="chip ${cls}">${escapeHtml(s)}</span>`).join('')
    || '<span class="muted">None found</span>';
}

function bullets(el, items, fmt = (x) => escapeHtml(x)) {
  el.innerHTML = (items || []).map(x => `<li>${fmt(x)}</li>`).join('') || '<li class="muted">None</li>';
}

function renderAnalysis(a) {
  document.getElementById('results').style.display = 'block';
  document.getElementById('summary').textContent = a.summary || '—';
  document.getElementById('profile-name').textContent = a.full_name || 'Unknown name';
  document.getElementById('profile-email').textContent = a.email || 'No email found';
  document.getElementById('profile-years').textContent = `Experience: ${a.years_of_experience} year(s)`;
  chips(document.getElementById('tech-skills'), a.technical_skills, 'tech');
  chips(document.getElementById('soft-skills'), a.soft_skills, 'soft');
  bullets(document.getElementById('education'), a.education,
    e => `${escapeHtml(e.degree)} — ${escapeHtml(e.institution)} (${escapeHtml(e.year)})`);
  bullets(document.getElementById('experience'), a.experience,
    e => `<strong>${escapeHtml(e.title)}</strong> at ${escapeHtml(e.company)} (${escapeHtml(e.duration)})` +
      ((e.highlights || []).length
        ? `<br><span class="muted">${e.highlights.map(escapeHtml).join(' · ')}</span>` : ''));
  bullets(document.getElementById('strengths'), a.strengths);
  bullets(document.getElementById('weaknesses'), a.weaknesses);
}

async function renderMatches(resumeId) {
  const box = document.getElementById('matches');
  try {
    const matches = await request(`/api/resumes/${resumeId}/matches`);
    if (!matches.length) {
      box.innerHTML = '<div class="empty">No job matches yet.</div>';
      return;
    }
    box.innerHTML = matches.map(m => `
      <div class="card">
        <div class="list-item"><h3>${escapeHtml(m.title)}</h3><span class="badge">${m.score}/100</span></div>
        <div class="muted">${escapeHtml(m.company)} · ${escapeHtml(m.location)}</div>
        <div class="scorebar"><span style="width:${Math.max(2, m.score)}%"></span></div>
        <div class="chips" style="margin:.4rem 0">${m.matched_skills.map(s => `<span class="chip tech">${escapeHtml(s)}</span>`).join('')}</div>
        <div class="chips">${m.missing_skills.map(s => `<span class="chip">${escapeHtml(s)}</span>`).join('')}</div>
        <p class="muted" style="margin-bottom:0">${escapeHtml(m.explanation)}</p>
      </div>`).join('');
  } catch (e) {
    box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`;
  }
}

async function handleFile(file) {
  const status = document.getElementById('upload-status');
  const errorBox = document.getElementById('error-box');
  errorBox.style.display = 'none';
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    errorBox.textContent = 'Only PDF or DOCX files are allowed.';
    errorBox.style.display = 'block';
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    errorBox.textContent = 'File is too large (max 5 MB).';
    errorBox.style.display = 'block';
    return;
  }
  status.textContent = 'Uploading and analyzing — this can take up to a minute…';
  const form = new FormData();
  form.append('file', file);
  try {
    const data = await request('/api/resumes', { method: 'POST', form });
    currentResumeId = data.resume_id;
    localStorage.setItem('resume_id', String(currentResumeId));
    status.textContent = `Analyzed ${file.name}`;
    renderAnalysis(data.analysis);
    await renderMatches(currentResumeId);
    toast('Resume analyzed');
  } catch (e) {
    status.textContent = '';
    errorBox.textContent = e.message;
    errorBox.style.display = 'block';
    toast(e.message, true);
  }
}

window.initPage = async () => {
  const dz = document.getElementById('dropzone');
  const input = document.getElementById('file');
  dz.addEventListener('click', () => input.click());
  dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', (e) => {
    e.preventDefault();
    dz.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => handleFile(input.files[0]));

  document.getElementById('improve-form').onsubmit = async (e) => {
    e.preventDefault();
    if (!currentResumeId) { toast('Upload a resume first', true); return; }
    const btn = e.target.querySelector('button');
    setBusy(btn, true, 'Planning…');
    try {
      const plan = await request(`/api/resumes/${currentResumeId}/improve`, {
        method: 'POST',
        body: { target_role: document.getElementById('target-role').value },
      });
      const box = document.getElementById('improve-plan');
      box.style.display = 'block';
      box.innerHTML = `
        <div class="grid cols-3">
          <div class="card"><h3>Missing skills</h3><div class="chips">${plan.missing_skills.map(s => `<span class="chip">${escapeHtml(s)}</span>`).join('') || '<span class="muted">None</span>'}</div></div>
          <div class="card"><h3>Improvements</h3><ul>${plan.improvements.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></div>
          <div class="card"><h3>Certifications</h3><ul>${plan.certifications.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></div>
        </div>
        <div class="card" style="margin-top:1rem"><h3>Learning resources</h3><ul>${plan.learning_resources.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>
        <h3 style="margin-top:.8rem">Weaknesses addressed</h3><ul>${plan.weaknesses.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul></div>`;
      toast('Improvement plan ready');
    } catch (err) {
      toast(err.message, true);
    } finally {
      setBusy(btn, false);
    }
  };

  const params = new URLSearchParams(location.search);
  const fromQuery = params.get('resume');
  const resumeId = fromQuery || localStorage.getItem('resume_id');
  if (resumeId) {
    try {
      const r = await request(`/api/resumes/${resumeId}`);
      if (r.analysis) {
        currentResumeId = r.id;
        localStorage.setItem('resume_id', String(r.id));
        document.getElementById('upload-status').textContent = `Showing ${r.filename}`;
        renderAnalysis(r.analysis);
        await renderMatches(r.id);
      }
    } catch (e) {
      localStorage.removeItem('resume_id');
    }
  }
};
