const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const money = (cents) => `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({ error: "Unexpected server response." }));
  if (!resp.ok) throw new Error(data.error || "Request failed.");
  return data;
}

// Checkout: fetch UPS rates for the address, then place the order with the chosen service.
const checkoutForm = document.getElementById("checkout-form");
if (checkoutForm) {
  const ratesBox = document.getElementById("rates");
  const errorBox = document.getElementById("checkout-error");
  const placeBtn = document.getElementById("place-order");
  const subtotal = Number(checkoutForm.dataset.subtotal);
  const address = () => Object.fromEntries(new FormData(checkoutForm));
  const showError = (msg) => { errorBox.textContent = msg; errorBox.hidden = !msg; };

  const updateTotals = () => {
    const chosen = checkoutForm.querySelector('input[name="service_code"]:checked');
    const shipping = chosen ? Number(chosen.dataset.amount) : null;
    document.getElementById("shipping-amount").textContent = shipping === null ? "choose a service" : money(shipping);
    document.getElementById("total-amount").textContent = money(subtotal + (shipping || 0));
    placeBtn.disabled = !chosen;
  };

  document.getElementById("get-rates").addEventListener("click", async () => {
    showError("");
    if (!checkoutForm.reportValidity()) return;
    ratesBox.querySelectorAll("label, p").forEach((el) => el.remove());
    try {
      const data = await postJSON(checkoutForm.dataset.ratesUrl, address());
      data.services.forEach((s, i) => {
        const label = document.createElement("label");
        label.className = "check";
        const input = Object.assign(document.createElement("input"), { type: "radio", name: "service_code", value: s.code, checked: i === 0 });
        input.dataset.amount = s.amount_cents;
        input.addEventListener("change", updateTotals);
        const days = s.business_days ? ` · ${s.business_days} business day${s.business_days > 1 ? "s" : ""}` : "";
        label.append(input, ` ${s.name} · ${money(s.amount_cents)}${days}`);
        ratesBox.append(label);
      });
      if (data.source === "estimate") {
        const note = Object.assign(document.createElement("p"), { className: "muted", textContent: "Estimated from UPS rate guidelines." });
        ratesBox.append(note);
      }
      ratesBox.hidden = false;
      updateTotals();
    } catch (err) {
      showError(err.message);
    }
  });

  checkoutForm.addEventListener("input", (e) => {
    if (["state", "zip"].includes(e.target.name)) { ratesBox.hidden = true; placeBtn.disabled = true; }
  });

  checkoutForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");
    placeBtn.disabled = true;
    try {
      const data = await postJSON(checkoutForm.dataset.checkoutUrl, address());
      window.location = data.redirect;
    } catch (err) {
      showError(err.message);
      placeBtn.disabled = false;
    }
  });
}

// Chat assistant. History lives in sessionStorage so it survives page navigation.
const chat = document.getElementById("chat");
if (chat) {
  const log = document.getElementById("chat-log");
  const input = document.getElementById("chat-input");
  const toggle = document.getElementById("chat-toggle");
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem("chat") || "[]"); } catch { history = []; }
  const save = () => { try { sessionStorage.setItem("chat", JSON.stringify(history.slice(-18))); } catch {} };

  const bubble = (role, text, links = []) => {
    const div = document.createElement("div");
    div.className = `bubble ${role}`;
    div.append(Object.assign(document.createElement("p"), { className: "pre", textContent: text }));
    if (links.length) {
      const box = Object.assign(document.createElement("div"), { className: "links" });
      links.forEach((l) => box.append(Object.assign(document.createElement("a"), { href: l.url, textContent: l.label })));
      div.append(box);
    }
    log.append(div);
    log.scrollTop = log.scrollHeight;
    return div;
  };
  history.forEach((m) => bubble(m.role, m.content, m.links));

  const setOpen = (open) => { chat.hidden = !open; toggle.setAttribute("aria-expanded", open); if (open) input.focus(); };
  toggle.addEventListener("click", () => setOpen(chat.hidden));
  document.getElementById("chat-close").addEventListener("click", () => setOpen(false));

  document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    history.push({ role: "user", content: text });
    bubble("user", text);
    const pending = bubble("assistant", "…");
    try {
      const messages = history.slice(-19).map(({ role, content }) => ({ role, content }));
      if (messages[0].role !== "user") messages.shift();
      const data = await postJSON("/api/chat", { messages });
      pending.remove();
      history.push({ role: "assistant", content: data.reply, links: data.links });
      bubble("assistant", data.reply, data.links);
    } catch (err) {
      pending.remove();
      history.pop();  // keep user/assistant turns alternating
      bubble("assistant", `Sorry, ${err.message}`);
    }
    save();
  });
}
