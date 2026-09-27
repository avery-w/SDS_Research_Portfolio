// Plain JS, loaded as a file so the CSP can forbid inline scripts.
const csrf = () => document.querySelector('meta[name="csrf-token"]').content;
const money = (c) => '$' + (c / 100).toFixed(2);

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ error: 'Something went wrong.' }));
  if (!res.ok) throw new Error(data.error || 'Something went wrong.');
  return data;
}

document.addEventListener('DOMContentLoaded', () => {
  const ratesBtn = document.getElementById('get-rates');
  if (ratesBtn) {
    const err = document.getElementById('rate-error');
    ratesBtn.addEventListener('click', async () => {
      err.hidden = true;
      try {
        const data = await postJSON(ratesBtn.dataset.url, { zip: document.getElementById('zip').value });
        for (const r of data.rates) {
          document.querySelector(`[data-rate="${r.service}"]`).textContent = `${money(r.cents)} (order total ${money(r.total_cents)})`;
        }
      } catch (e) {
        err.textContent = e.message;
        err.hidden = false;
      }
    });
  }

  const form = document.getElementById('chat-form');
  if (form) {
    const log = document.getElementById('chat-log');
    const input = document.getElementById('chat-input');
    const history = [];
    const add = (role, text) => {
      const p = document.createElement('p');
      p.className = 'chat-' + role;
      p.textContent = text; // never innerHTML: model output is untrusted
      log.append(p);
      log.scrollTop = log.scrollHeight;
    };
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      add('user', text);
      history.push({ role: 'user', content: text });
      const button = form.querySelector('button');
      button.disabled = true;
      try {
        const data = await postJSON('/api/chat', { messages: history.slice(-19) });
        history.push({ role: 'assistant', content: data.reply });
        add('assistant', data.reply);
      } catch (e) {
        history.pop();
        add('error', e.message);
      } finally {
        button.disabled = false;
      }
    });
  }
});
