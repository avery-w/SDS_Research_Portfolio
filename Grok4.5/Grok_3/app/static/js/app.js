const API = "";
let token = localStorage.getItem("token") || null;
let currentUser = null;

function headers(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { ...headers(!(opts.body instanceof FormData)), ...(opts.headers || {}) },
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((x) => x.msg || JSON.stringify(x)).join("; ") : d || res.statusText);
  }
  return data;
}

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showSection(name) {
  document.querySelectorAll(".section").forEach((el) => el.classList.add("hidden"));
  $("hero")?.classList.toggle("hidden", name !== "home");
  $(`section-${name}`)?.classList.remove("hidden");
  if (name === "products") loadProducts();
  if (name === "cart") loadCart();
  if (name === "orders") loadOrders();
  if (name === "seller") loadSeller();
  if (name === "admin") loadAdmin();
}

function updateAuthUI() {
  const area = $("auth-area");
  if (!area) return;
  if (token && currentUser) {
    let extra = "";
    if (currentUser.role === "seller") extra += `<a href="#" data-section="seller">Seller</a>`;
    if (currentUser.role === "admin") extra += `<a href="#" data-section="admin">Admin</a>`;
    area.innerHTML = `<span style="color:var(--muted);font-size:.85rem">${esc(currentUser.email)}</span>${extra}<a href="#" id="btn-logout">Logout</a>`;
    $("btn-logout")?.addEventListener("click", (e) => { e.preventDefault(); logout(); });
  } else {
    area.innerHTML = `<a href="#" data-section="login">Login</a><a href="#" data-section="register">Register</a>`;
  }
  area.querySelectorAll("[data-section]").forEach((a) => {
    a.addEventListener("click", (e) => { e.preventDefault(); showSection(a.dataset.section); });
  });
}

async function loadMe() {
  if (!token) { updateAuthUI(); return; }
  try { currentUser = await api("/auth/me"); updateAuthUI(); }
  catch { token = null; localStorage.removeItem("token"); currentUser = null; updateAuthUI(); }
}

function logout() {
  token = null; currentUser = null; localStorage.removeItem("token");
  updateAuthUI(); showSection("login");
}

$("form-login")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const body = new URLSearchParams({ username: $("login-email").value, password: $("login-password").value });
    const res = await fetch("/auth/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    token = data.access_token; localStorage.setItem("token", token);
    await loadMe();
    showSection(currentUser?.role === "seller" ? "seller" : currentUser?.role === "admin" ? "admin" : "products");
  } catch (err) { alert(err.message); }
});

$("form-register")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: $("reg-email").value, password: $("reg-password").value,
        full_name: $("reg-name").value, role: $("reg-role").value,
      }),
    });
    alert("Account created! Please sign in."); showSection("login");
  } catch (err) { alert(err.message); }
});

async function loadProducts() {
  const list = $("product-list"); if (!list) return;
  list.innerHTML = `<p class="empty">Loading…</p>`;
  try {
    const q = $("search-q")?.value || "";
    const products = await api(`/customer/products?q=${encodeURIComponent(q)}`);
    if (!products.length) { list.innerHTML = `<p class="empty">No products found.</p>`; return; }
    list.innerHTML = products.map((p) => `
      <div class="card">
        ${p.image_path ? `<img src="/uploads/${esc(p.image_path)}" alt="" loading="lazy" />` : `<div class="placeholder"></div>`}
        <h3>${esc(p.name)}</h3>
        <div class="price">$${p.price.toFixed(2)}</div>
        <div class="meta">${p.inventory} in stock</div>
        <p class="meta">${esc((p.description || "").slice(0, 70))}</p>
        <button class="btn primary sm" data-add="${p.id}">Add to Cart</button>
      </div>`).join("");
    list.querySelectorAll("[data-add]").forEach((b) => b.addEventListener("click", () => addToCart(+b.dataset.add)));
  } catch (err) { list.innerHTML = `<p class="empty">${esc(err.message)}</p>`; }
}

async function addToCart(id) {
  if (!token) return alert("Please log in as a customer.");
  try { await api("/customer/cart", { method: "POST", body: JSON.stringify({ product_id: id, quantity: 1 }) }); alert("Added to cart"); }
  catch (err) { alert(err.message); }
}

async function loadCart() {
  const list = $("cart-list"), actions = $("cart-actions");
  if (!token) { list.innerHTML = `<p class="empty">Please log in.</p>`; actions?.classList.add("hidden"); return; }
  try {
    const items = await api("/customer/cart");
    if (!items.length) { list.innerHTML = `<p class="empty">Cart is empty.</p>`; actions?.classList.add("hidden"); return; }
    let total = 0;
    list.innerHTML = `<table><thead><tr><th>Product</th><th>Qty</th><th>Price</th><th></th></tr></thead><tbody>
      ${items.map((i) => { total += i.product.price * i.quantity;
        return `<tr><td>${esc(i.product.name)}</td><td>${i.quantity}</td><td>$${(i.product.price * i.quantity).toFixed(2)}</td>
        <td><button class="btn danger sm" data-rm="${i.id}">Remove</button></td></tr>`; }).join("")}
    </tbody></table><p style="margin-top:.9rem;font-weight:600">Subtotal: $${total.toFixed(2)}</p>`;
    list.querySelectorAll("[data-rm]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/customer/cart/${b.dataset.rm}`, { method: "DELETE" }); loadCart(); } catch (e) { alert(e.message); }
    }));
    actions?.classList.remove("hidden");
  } catch (err) { list.innerHTML = `<p class="empty">${esc(err.message)}</p>`; }
}

$("btn-checkout")?.addEventListener("click", async () => {
  const address = $("ship-address").value.trim(), zip = $("ship-zip").value.trim();
  if (!address || !zip) return alert("Address and ZIP required.");
  try {
    const items = await api("/customer/cart");
    let weight = 0, l = 0, w = 0, h = 0;
    items.forEach((i) => { weight += i.product.weight_lb * i.quantity; l = Math.max(l, i.product.length_in); w = Math.max(w, i.product.width_in); h = Math.max(h, i.product.height_in); });
    const rates = await api("/api/shipping/rates", { method: "POST", body: JSON.stringify({ dest_zip: zip, weight_lb: weight || 1, length_in: l || 10, width_in: w || 8, height_in: h || 4 }) });
    const preview = $("ship-preview"); preview.textContent = JSON.stringify(rates, null, 2); preview.classList.remove("hidden");
    if (!confirm(`Shipping ≈ $${rates.shipping_cost}. Place order?`)) return;
    const order = await api("/api/checkout", { method: "POST", body: JSON.stringify({ shipping_address: address, shipping_zip: zip }) });
    alert(`Order #${order.id} placed! Total $${order.total.toFixed(2)}`); loadCart(); showSection("orders");
  } catch (err) { alert(err.message); }
});

async function loadOrders() {
  const list = $("order-list"); if (!token) { list.innerHTML = `<p class="empty">Please log in.</p>`; return; }
  try {
    const orders = await api("/customer/orders");
    if (!orders.length) { list.innerHTML = `<p class="empty">No orders yet.</p>`; return; }
    list.innerHTML = orders.map((o) => `
      <div class="card" style="margin-bottom:.85rem">
        <strong>Order #${o.id}</strong> <span class="meta">· ${o.status} · $${o.total.toFixed(2)}</span>
        <div class="meta">${new Date(o.created_at).toLocaleString()}</div>
        <div class="meta">Ship to: ${esc(o.shipping_address)} (${esc(o.shipping_zip)})</div>
        <div style="margin-top:.5rem;display:flex;gap:.4rem">
          ${["pending","paid"].includes(o.status) ? `<button class="btn sm" data-cancel="${o.id}">Cancel</button>` : ""}
          ${["shipped","delivered"].includes(o.status) ? `<button class="btn sm" data-return="${o.id}">Request Return</button>` : ""}
        </div>
      </div>`).join("");
    list.querySelectorAll("[data-cancel]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/customer/orders/${b.dataset.cancel}/cancel`, { method: "POST" }); loadOrders(); } catch (e) { alert(e.message); }
    }));
    list.querySelectorAll("[data-return]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/customer/orders/${b.dataset.return}/return`, { method: "POST" }); loadOrders(); } catch (e) { alert(e.message); }
    }));
  } catch (err) { list.innerHTML = `<p class="empty">${esc(err.message)}</p>`; }
}

$("btn-chat")?.addEventListener("click", sendChat);
$("chat-msg")?.addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });
async function sendChat() {
  const input = $("chat-msg"), msg = input.value.trim();
  if (!msg) return; if (!token) return alert("Please log in.");
  const box = $("chat-box");
  box.innerHTML += `<div class="chat-msg user"><span class="bubble">${esc(msg)}</span></div>`;
  input.value = ""; box.scrollTop = box.scrollHeight;
  try {
    const data = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: msg }) });
    box.innerHTML += `<div class="chat-msg bot"><span class="bubble">${esc(data.reply)}</span></div>`;
  } catch (err) { box.innerHTML += `<div class="chat-msg bot"><span class="bubble">Error: ${esc(err.message)}</span></div>`; }
  box.scrollTop = box.scrollHeight;
}

async function loadSeller() {
  if (!currentUser || currentUser.role !== "seller") return;
  try {
    const store = await api("/seller/store");
    $("seller-info").innerHTML = `<strong>${esc(store.name)}</strong> — ${esc(store.description || "")}`;
    const products = await api("/seller/products");
    $("seller-products").innerHTML = products.length ? products.map((p) => `
      <div class="card"><h3>${esc(p.name)}</h3><div class="price">$${p.price.toFixed(2)}</div>
      <div class="meta">Stock ${p.inventory} · ${p.is_active ? "Active" : "Inactive"}</div></div>`).join("") : `<p class="empty">No products yet.</p>`;
    const orders = await api("/seller/orders");
    $("seller-orders").innerHTML = orders.length ? orders.map((o) => `
      <div class="card" style="margin-bottom:.6rem">Order #${o.id} · <strong>${o.status}</strong> · $${o.total.toFixed(2)}
      ${o.status === "paid" ? `<button class="btn sm" style="margin-left:.5rem" data-ship="${o.id}">Mark Shipped</button>` : ""}</div>`).join("") : `<p class="empty">No orders yet.</p>`;
    $("seller-orders").querySelectorAll("[data-ship]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/seller/orders/${b.dataset.ship}/status?status=shipped`, { method: "PATCH" }); loadSeller(); } catch (e) { alert(e.message); }
    }));
  } catch (err) { alert(err.message); }
}

$("product-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData();
  fd.append("name", $("p-name").value); fd.append("description", $("p-desc").value);
  fd.append("price", $("p-price").value); fd.append("inventory", $("p-inv").value);
  fd.append("weight_lb", $("p-weight").value);
  const img = $("p-image").files[0]; if (img) fd.append("image", img);
  try {
    const res = await fetch("/seller/products", { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    alert("Product published!"); e.target.reset(); loadSeller();
  } catch (err) { alert(err.message); }
});

async function loadAdmin() {
  if (!currentUser || currentUser.role !== "admin") return;
  try {
    const a = await api("/admin/analytics");
    $("admin-analytics").innerHTML = `
      <div class="stat"><div class="value">$${a.total_revenue.toFixed(0)}</div><div class="label">Revenue</div></div>
      <div class="stat"><div class="value">${a.order_count}</div><div class="label">Orders</div></div>
      <div class="stat"><div class="value">${a.active_users}</div><div class="label">Users</div></div>
      <div class="stat"><div class="value">${a.active_stores}</div><div class="label">Stores</div></div>
      <div class="stat"><div class="value">${a.active_products}</div><div class="label">Products</div></div>`;
    const users = await api("/admin/users");
    $("admin-users").innerHTML = `<table><thead><tr><th>ID</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead><tbody>
      ${users.map((u) => `<tr><td>${u.id}</td><td>${esc(u.email)}</td><td>${u.role}</td><td>${u.is_active}</td><td>
        ${u.is_active && u.role !== "admin" ? `<button class="btn danger sm" data-deact="${u.id}">Deactivate</button>` : ""}
        ${!u.is_active ? `<button class="btn sm" data-act="${u.id}">Activate</button>` : ""}
      </td></tr>`).join("")}</tbody></table>`;
    $("admin-users").querySelectorAll("[data-deact]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/admin/users/${b.dataset.deact}/deactivate`, { method: "PATCH" }); loadAdmin(); } catch (e) { alert(e.message); }
    }));
    $("admin-users").querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", async () => {
      try { await api(`/admin/users/${b.dataset.act}/activate`, { method: "PATCH" }); loadAdmin(); } catch (e) { alert(e.message); }
    }));
    const orders = await api("/admin/orders?limit=20");
    $("admin-orders").innerHTML = orders.length
      ? orders.map((o) => `<div class="card" style="margin-bottom:.5rem">#${o.id} · ${o.status} · $${o.total.toFixed(2)} · ${new Date(o.created_at).toLocaleDateString()}</div>`).join("")
      : `<p class="empty">No orders.</p>`;
  } catch (err) { alert(err.message); }
}

document.querySelectorAll("[data-section]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    const sec = el.dataset.section;
    if (sec === "home") { document.querySelectorAll(".section").forEach((s) => s.classList.add("hidden")); $("hero")?.classList.remove("hidden"); }
    else showSection(sec);
  });
});
$("btn-search")?.addEventListener("click", loadProducts);
$("search-q")?.addEventListener("keydown", (e) => { if (e.key === "Enter") loadProducts(); });
loadMe();
