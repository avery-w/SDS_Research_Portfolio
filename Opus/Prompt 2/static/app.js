// Confirm destructive actions: <form data-confirm="Are you sure?">
document.addEventListener("submit", (e) => {
  const msg = e.target.dataset.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});

// Flash toasts fade out on their own.
setTimeout(() => document.querySelectorAll(".flash").forEach((f) => f.remove()), 6000);

async function postJSON(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.message || Object.values(data.fields || {}).join(" ") || "Request failed"), { data });
  return data;
}
const usd = (n) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// ---------- checkout: live UPS quotes ----------
const checkout = document.getElementById("checkout-form");
if (checkout) {
  const zip = checkout.querySelector("[name=zip]");
  const box = document.getElementById("ship-options");
  const subtotal = Number(checkout.dataset.subtotal);
  const taxRate = Number(checkout.dataset.tax);
  const submit = checkout.querySelector("button[type=submit]");
  let timer;
  const renderTotals = () => {
    const picked = checkout.querySelector("[name=service]:checked");
    const ship = picked ? Number(picked.dataset.total) : 0;
    const tax = Math.round(subtotal * taxRate / 100) / 100;
    document.getElementById("t-ship").textContent = picked ? (ship === 0 ? "FREE" : usd(ship)) : "Enter ZIP";
    document.getElementById("t-tax").textContent = usd(tax);
    document.getElementById("t-total").textContent = usd(subtotal / 100 + ship + tax);
    submit.disabled = !picked;
  };
  const quote = async () => {
    const z = zip.value.trim();
    if (!/^\d{5}(-\d{4})?$/.test(z)) { box.innerHTML = '<p class="muted small">Enter a ZIP code to see UPS rates.</p>'; renderTotals(); return; }
    box.innerHTML = '<p class="muted small typing">Rating with UPS</p>';
    try {
      const q = await postJSON("/api/shipping/rates", { zip: z });
      box.innerHTML = `<p class="muted small">Zone ${q.zone} · ${q.distance_mi} mi from Austin, TX · ${q.options[0].packages} package(s), ${q.options[0].billable_lb} lb billable</p>` +
        q.options.map((o, i) => `<label class="shipopt"><input type="radio" name="service" value="${o.service}" data-total="${o.total}" ${i === 0 ? "checked" : ""}>
          <span class="grow"><strong>${esc(o.name)}</strong><br><span class="muted small">${o.transit_days} business day${o.transit_days > 1 ? "s" : ""}${o.surcharges ? ` · incl. ${usd(o.surcharges)} surcharges` : ""} · fuel ${usd(o.fuel)}</span></span>
          <strong>${o.free ? `<s class="muted small">${usd(o.list_total)}</s> FREE` : usd(o.total)}</strong></label>`).join("");
    } catch (err) {
      box.innerHTML = `<p class="badge bad">${esc(err.message)}</p>`;
    }
    renderTotals();
  };
  zip.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(quote, 350); });
  box.addEventListener("change", renderTotals);
  quote();
}

// ---------- Bevo Bot chat widget ----------
const fab = document.getElementById("chat-fab");
if (fab) {
  const panel = document.getElementById("chat-panel");
  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = form.querySelector("input");
  const KEY = "bevo-chat";
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch { history = []; }

  const bubble = (role, text, actions = []) => {
    const el = document.createElement("div");
    el.className = `bubble ${role === "user" ? "me" : "them"}`;
    el.textContent = text;
    log.appendChild(el);
    if (actions.length) {
      const row = document.createElement("div");
      row.className = "actions";
      actions.forEach((a) => { const l = document.createElement("a"); l.className = "btn sm ghost"; l.href = a.url; l.textContent = a.label; row.appendChild(l); });
      log.appendChild(row);
    }
    log.scrollTop = log.scrollHeight;
    return el;
  };
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-30))); } catch {} };

  bubble("assistant", "Hi! I'm Bevo Bot 🤘 I can find products, estimate UPS shipping, and check your orders. For product or order specifics, I'll connect you with the seller directly.");
  history.forEach((m) => bubble(m.role, m.content, m.actions || []));

  fab.addEventListener("click", () => { panel.classList.toggle("open"); if (panel.classList.contains("open")) input.focus(); });
  document.getElementById("chat-close").addEventListener("click", () => panel.classList.remove("open"));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    history.push({ role: "user", content: text });
    bubble("user", text);
    const wait = bubble("assistant", "Thinking");
    wait.classList.add("typing");
    form.querySelector("button").disabled = true;
    try {
      let recent = history.slice(-29);
      if (recent[0].role !== "user") recent = recent.slice(1);
      const res = await postJSON("/api/chat", { messages: recent.map(({ role, content }) => ({ role, content })) });
      wait.remove();
      history.push({ role: "assistant", content: res.reply, actions: res.actions });
      bubble("assistant", res.reply, res.actions);
    } catch (err) {
      wait.remove();
      history.pop();
      bubble("assistant", `Sorry, ${err.message}`);
    }
    // Keep strict user/assistant alternation for the API even after errors.
    if (history.length && history[0].role !== "user") history.shift();
    save();
    form.querySelector("button").disabled = false;
    input.focus();
  });
}
