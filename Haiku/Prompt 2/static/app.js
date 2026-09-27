"use strict";
const CSRF = document.querySelector('meta[name="csrf-token"]').content;
const money = (c) => "$" + (c / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function api(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({ error: "Unexpected server response." }));
  if (!res.ok) throw new Error(data.error || "Request failed.");
  return data;
}

// Confirm destructive form submissions.
document.addEventListener("submit", (e) => {
  const msg = e.target.dataset && e.target.dataset.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});

// ---------------------------------------------------------------- checkout
const checkout = document.getElementById("checkout-form");
if (checkout) {
  const ratesBox = document.getElementById("rates");
  const placeBtn = document.getElementById("place-order");
  const errBox = document.getElementById("checkout-error");
  const sub = Number(document.getElementById("t-sub").dataset.cents);
  const taxRate = Number(document.getElementById("t-tax").dataset.rate);
  const tax = Math.round((sub * taxRate) / 100);
  document.getElementById("t-tax").textContent = money(tax);
  const field = (n) => checkout.elements[n].value.trim();
  const showError = (msg) => { errBox.textContent = msg; errBox.hidden = !msg; };

  function updateTotals() {
    const picked = checkout.querySelector('input[name="service"]:checked');
    const ship = picked ? Number(picked.dataset.cents) : null;
    document.getElementById("t-ship").textContent = ship === null ? "Enter ZIP" : ship === 0 ? "Free" : money(ship);
    document.getElementById("t-total").textContent = ship === null ? "…" : money(sub + ship + tax);
    placeBtn.disabled = !picked;
  }

  async function loadRates() {
    showError("");
    const zip = field("zip");
    if (!/^\d{5}(-\d{4})?$/.test(zip)) { showError("Enter a valid ZIP code to see UPS rates."); return; }
    ratesBox.textContent = "Getting UPS rates…";
    try {
      const q = await api("/api/shipping/rates", { zip });
      ratesBox.replaceChildren();
      const d = q.destination;
      const info = document.createElement("p");
      info.className = "muted small";
      info.textContent = `Austin, TX → ${d.zip} (${d.state}) · UPS zone ${d.zone} · ~${d.distance_mi} mi · ${q.shipments.reduce((n, s) => n + s.packages.length, 0)} package(s)`;
      ratesBox.append(info);
      q.services.forEach((s, i) => {
        const label = document.createElement("label");
        label.className = "rate";
        const input = Object.assign(document.createElement("input"), { type: "radio", name: "service", value: s.code, checked: i === 0 });
        input.dataset.cents = s.cents;
        const text = document.createElement("span");
        text.className = "grow";
        const when = new Date(s.delivery_date + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
        text.innerHTML = "<b></b><small></small>";
        text.querySelector("b").textContent = s.name;
        text.querySelector("small").textContent = `Arrives by ${when} · ${s.transit_days} business day${s.transit_days > 1 ? "s" : ""}`;
        const price = document.createElement("b");
        price.textContent = s.cents === 0 ? "Free" : money(s.cents);
        label.append(input, text, price);
        ratesBox.append(label);
      });
      updateTotals();
    } catch (err) {
      ratesBox.replaceChildren();
      showError(err.message);
      updateTotals();
    }
  }

  document.getElementById("get-rates").addEventListener("click", loadRates);
  checkout.elements.zip.addEventListener("change", loadRates);
  ratesBox.addEventListener("change", updateTotals);
  if (/^\d{5}/.test(field("zip"))) loadRates();

  checkout.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!checkout.reportValidity()) return;
    const picked = checkout.querySelector('input[name="service"]:checked');
    if (!picked) return showError("Choose a shipping option.");
    placeBtn.disabled = true;
    placeBtn.textContent = "Placing order…";
    try {
      const res = await api("/api/checkout", {
        service: picked.value, name: field("name"), street: field("street"), city: field("city"),
        state: field("state").toUpperCase(), zip: field("zip"), save_address: checkout.elements.save_address.checked,
      });
      window.location = res.redirect;
    } catch (err) {
      showError(err.message);
      placeBtn.disabled = false;
      placeBtn.textContent = "Place order";
    }
  });
}

// ---------------------------------------------------------------- Scout chat
const chat = document.getElementById("chat");
if (chat) {
  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const fab = document.getElementById("chat-open");
  const KEY = "scout-history";
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch { history = []; }
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-18))); } catch { /* storage blocked */ } };

  function bubble(role, text, suggestions) {
    const div = document.createElement("div");
    div.className = "msg " + (role === "user" ? "me" : "bot");
    div.textContent = text;
    log.append(div);
    if (suggestions && suggestions.length) {
      const wrap = document.createElement("div");
      wrap.className = "suggestions";
      for (const s of suggestions) {
        if (!s.url.startsWith("/")) continue;  // only same-site links
        const a = Object.assign(document.createElement("a"), { href: s.url, textContent: s.label });
        wrap.append(a);
      }
      log.append(wrap);
    }
    log.scrollTop = log.scrollHeight;
    return div;
  }
  history.forEach((m) => bubble(m.role, m.content));

  const toggle = (open) => { chat.hidden = !open; fab.setAttribute("aria-expanded", open); if (open) input.focus(); };
  fab.addEventListener("click", () => toggle(chat.hidden));
  document.getElementById("chat-close").addEventListener("click", () => toggle(false));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    bubble("user", text);
    history.push({ role: "user", content: text });
    const typing = bubble("bot", "Scout is typing…");
    typing.classList.add("typing");
    try {
      // The API expects user/assistant alternation starting with a user turn, max 20 turns.
      let turns = history.slice(-19);
      if (turns[0].role !== "user") turns = turns.slice(1);
      const res = await api("/api/chat", { messages: turns });
      typing.remove();
      bubble("bot", res.reply, res.suggestions);
      history.push({ role: "assistant", content: res.reply });
    } catch (err) {
      typing.remove();
      bubble("bot", err.message);
      history.pop();
    }
    save();
  });
}
