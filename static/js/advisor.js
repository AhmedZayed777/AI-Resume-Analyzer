const history = [];

function addMsg(text, who, isError = false) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = `msg ${who}` + (isError ? ' error' : '');
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
  return el;
}

window.initPage = async () => {
  try {
    const resumes = await request('/api/resumes');
    const select = document.getElementById('resume-select');
    resumes.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.id;
      opt.textContent = `${r.filename} — ${r.full_name || 'unknown'}`;
      select.appendChild(opt);
    });
  } catch (e) { /* select stays "No resume" */ }

  document.getElementById('ask-form').onsubmit = async (e) => {
    e.preventDefault();
    const input = document.getElementById('question');
    const question = input.value.trim();
    if (!question) return;
    addMsg(question, 'user');
    history.push({ role: 'user', content: question });
    input.value = '';
    const btn = e.target.querySelector('button');
    const thinking = addMsg('Thinking…', 'assistant');
    setBusy(btn, true, '…');
    try {
      const resumeId = document.getElementById('resume-select').value;
      const data = await request('/api/advisor/ask', {
        method: 'POST',
        body: {
          question,
          resume_id: resumeId ? Number(resumeId) : null,
          history: history.slice(-10, -1),
        },
      });
      thinking.remove();
      addMsg(data.answer, 'assistant');
      history.push({ role: 'assistant', content: data.answer });
    } catch (err) {
      thinking.remove();
      addMsg(err.message, 'assistant', true);
    } finally {
      setBusy(btn, false);
    }
  };
};
