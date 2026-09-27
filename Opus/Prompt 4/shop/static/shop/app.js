// Chat widget and checkout shipping rates. All server text goes through textContent, never innerHTML.
function csrf(form) {
  return form.querySelector("[name=csrfmiddlewaretoken]").value;
}

async function postJSON(url, form, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(form) },
    body: JSON.stringify(body),
  });
  return resp.json().catch(() => ({ error: "Something went wrong." }));
}

function line(parent, cls, text) {
  const p = document.createElement("p");
  p.className = cls;
  p.textContent = text;
  parent.appendChild(p);
  parent.scrollTop = parent.scrollHeight;
}

document.addEventListener("DOMContentLoaded", () => {
  const chat = document.getElementById("chat-form");
  if (chat) {
    const log = document.getElementById("chat-log");
    chat.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = chat.elements.message;
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      line(log, "me", text);
      chat.querySelector("button").disabled = true;
      const data = await postJSON(chat.dataset.url, chat, { message: text });
      chat.querySelector("button").disabled = false;
      line(log, "bot", data.reply || data.error);
    });
  }

  const checkout = document.getElementById("checkout");
  if (checkout) {
    const out = document.getElementById("rates");
    document.getElementById("get-rates").addEventListener("click", async () => {
      const f = checkout.elements;
      out.textContent = "Calculating…";
      const data = await postJSON(checkout.dataset.ratesUrl, checkout, {
        name: f.name.value, line1: f.line1.value, city: f.city.value, state: f.state.value, zip: f.zip.value,
      });
      out.textContent = "";
      if (data.error) return line(out, "error", data.error);
      for (const r of data.rates) {
        const opt = [...f.service.options].find((o) => o.value === r.code);
        if (opt) opt.textContent = `${r.service}: $${r.amount}`;
      }
      line(out, "", `${data.shipments} shipment(s) from ${data.origin}` +
        (data.source === "estimate" ? " (estimated UPS rates)" : " (UPS rates)") + ". Choose a service above.");
    });
  }
});
