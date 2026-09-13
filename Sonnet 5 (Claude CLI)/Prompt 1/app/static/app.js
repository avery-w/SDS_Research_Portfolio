// ---- state ----
let token = localStorage.getItem("token") || null;
let currentUser = null; // {id, email, name, role}
let checkoutQuote = null;
let cartCache = [];

// ---- api helper ----
async function api(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let payload = body;
  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(path, { method, headers, body: payload });
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const message = (data && data.detail) || `Request failed (${res.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return data;
}

function money(cents) { return `$${(cents / 100).toFixed(2)}`; }
function badge(status) { return `<span class="badge ${status}">${status.replace(/_/g, " ")}</span>`; }

// ---- routing ----
const VIEWS = ["browse", "product", "auth", "cart", "checkout", "orders", "messages", "seller", "admin"];
function go(view, opts = {}) {
  if (view !== "auth" && needsAuth(view) && !currentUser) { go("auth"); return; }
  VIEWS.forEach((v) => document.getElementById(`view-${v}`).classList.toggle("active", v === view));
  renderNav(view);
  if (view === "browse") loadProducts();
  if (view === "product") loadProductDetail(opts.id);
  if (view === "cart") loadCart();
  if (view === "checkout") loadCheckout();
  if (view === "orders") loadOrders();
  if (view === "messages") loadMessages();
  if (view === "seller") loadSellerStore();
  if (view === "admin") loadAdminAnalytics();
}
function needsAuth(view) {
  return ["cart", "checkout", "orders", "messages", "seller", "admin"].includes(view);
}

function renderNav(active) {
  const nav = document.getElementById("main-nav");
  const items = [["browse", "Browse"]];
  if (currentUser) {
    if (currentUser.role === "customer") { items.push(["cart", "Cart"], ["orders", "Orders"], ["messages", "Messages"]); }
    if (currentUser.role === "seller") { items.push(["seller", "Seller Dashboard"], ["messages", "Messages"]); }
    if (currentUser.role === "admin") { items.push(["admin", "Admin Dashboard"]); }
  }
  nav.innerHTML = items.map(([v, label]) => `<button class="${v === active ? "active" : ""}" onclick="go('${v}')">${label}</button>`).join("");

  const account = document.getElementById("account-area");
  if (currentUser) {
    account.innerHTML = `<span class="muted">${currentUser.name} (${currentUser.role})</span> <button class="secondary" onclick="logout()">Log out</button>`;
  } else {
    account.innerHTML = `<button onclick="go('auth')">Log in / Sign up</button>`;
  }
}

// ---- auth ----
function setAuthTab(tab) {
  document.getElementById("tab-login").classList.toggle("active", tab === "login");
  document.getElementById("tab-register").classList.toggle("active", tab === "register");
  document.getElementById("login-form").style.display = tab === "login" ? "block" : "none";
  document.getElementById("register-form").style.display = tab === "register" ? "block" : "none";
}

async function submitLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  try {
    const data = await api("/api/auth/login", { method: "POST", body: { email, password } });
    await afterLogin(data);
  } catch (err) {
    document.getElementById("login-error").textContent = err.message;
  }
  return false;
}

async function submitRegister(e) {
  e.preventDefault();
  const body = {
    name: document.getElementById("reg-name").value,
    email: document.getElementById("reg-email").value,
    password: document.getElementById("reg-password").value,
    role: document.getElementById("reg-role").value,
  };
  try {
    const data = await api("/api/auth/register", { method: "POST", body });
    await afterLogin(data);
  } catch (err) {
    document.getElementById("register-error").textContent = err.message;
  }
  return false;
}

async function afterLogin(data) {
  token = data.access_token;
  localStorage.setItem("token", token);
  currentUser = await api("/api/auth/me");
  go("browse");
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem("token");
  go("browse");
}

async function restoreSession() {
  if (!token) { go("browse"); return; }
  try {
    currentUser = await api("/api/auth/me");
  } catch (_) {
    token = null;
    localStorage.removeItem("token");
  }
  go("browse");
}

// ---- browse / product ----
async function loadProducts() {
  const grid = document.getElementById("product-grid");
  grid.innerHTML = "Loading...";
  const q = document.getElementById("search-input").value.trim();
  const category = document.getElementById("category-filter").value;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  try {
    const products = await api(`/api/products?${params}`);
    grid.innerHTML = products.map(productCard).join("") || `<p class="muted">No products found.</p>`;
    const cats = [...new Set(products.map((p) => p.category))];
    const select = document.getElementById("category-filter");
    const current = select.value;
    select.innerHTML = `<option value="">All categories</option>` + cats.map((c) => `<option value="${c}">${c}</option>`).join("");
    select.value = current;
  } catch (err) {
    grid.innerHTML = `<p class="error">${err.message}</p>`;
  }
}
function doSearch() { go("browse"); loadProducts(); }

function productCard(p) {
  const img = p.images[0] || "";
  return `<div class="card product-card" onclick="go('product', {id: ${p.id}})">
    ${img ? `<img src="${img}" />` : `<div style="height:160px;background:#eee;border-radius:10px;"></div>`}
    <h3>${escapeHtml(p.name)}</h3>
    <div class="price">${money(p.price_cents)}</div>
    <div class="muted">${p.stock_qty > 0 ? p.stock_qty + " in stock" : "Out of stock"}</div>
  </div>`;
}

async function loadProductDetail(id) {
  const el = document.getElementById("product-detail");
  el.innerHTML = "Loading...";
  try {
    const p = await api(`/api/products/${id}`);
    el.innerHTML = `
      <div class="card">
        <div class="image-thumbs">${p.images.map((i) => `<img src="${i}" />`).join("") || "<p class='muted'>No images</p>"}</div>
        <h2>${escapeHtml(p.name)}</h2>
        <p>${escapeHtml(p.description)}</p>
        <p class="muted">Category: ${p.category}</p>
        <div class="price" style="font-size:1.4rem">${money(p.price_cents)}</div>
        <p class="muted">${p.stock_qty} in stock</p>
        <div class="form-inline">
          <input type="number" id="add-qty" value="1" min="1" style="width:70px" />
          <button onclick="addToCart(${p.id})" ${p.stock_qty < 1 ? "disabled" : ""}>Add to cart</button>
          <button class="secondary" onclick="messageSellerAbout(${p.id}, ${p.store_id})">Message seller</button>
        </div>
        <p class="error" id="product-action-error"></p>
      </div>`;
  } catch (err) {
    el.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

async function addToCart(productId) {
  if (!currentUser) return go("auth");
  const qty = parseInt(document.getElementById("add-qty").value, 10) || 1;
  try {
    await api("/api/cart", { method: "POST", body: { product_id: productId, quantity: qty } });
    go("cart");
  } catch (err) {
    document.getElementById("product-action-error").textContent = err.message;
  }
}

function messageSellerAbout(productId, storeId) {
  if (!currentUser) return go("auth");
  go("messages");
  document.getElementById("msg-body").placeholder = `Question about product #${productId}...`;
  window._pendingMessageProduct = productId;
}

// ---- cart ----
async function loadCart() {
  const el = document.getElementById("cart-items");
  el.innerHTML = "Loading...";
  try {
    cartCache = await api("/api/cart");
    if (cartCache.length === 0) {
      el.innerHTML = `<p class="muted">Your cart is empty.</p>`;
      document.getElementById("cart-summary").innerHTML = "";
      return;
    }
    el.innerHTML = cartCache.map((i) => `
      <div class="card form-inline" style="justify-content:space-between">
        <div><strong>${escapeHtml(i.name)}</strong><div class="muted">${money(i.price_cents)} each</div></div>
        <input type="number" min="1" value="${i.quantity}" style="width:70px" onchange="updateCartItem(${i.id}, ${i.product_id}, this.value)" />
        <button class="danger" onclick="removeCartItem(${i.id})">Remove</button>
      </div>`).join("");
    const subtotal = cartCache.reduce((s, i) => s + i.price_cents * i.quantity, 0);
    document.getElementById("cart-summary").innerHTML = `
      <p>Subtotal: <strong>${money(subtotal)}</strong></p>
      <button onclick="go('checkout')">Checkout</button>`;
  } catch (err) {
    el.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

async function updateCartItem(itemId, productId, qty) {
  try {
    await api(`/api/cart/${itemId}`, { method: "PATCH", body: { product_id: productId, quantity: parseInt(qty, 10) } });
    loadCart();
  } catch (err) { alert(err.message); }
}
async function removeCartItem(itemId) {
  try { await api(`/api/cart/${itemId}`, { method: "DELETE" }); loadCart(); } catch (err) { alert(err.message); }
}

// ---- checkout ----
function loadCheckout() {
  checkoutQuote = null;
  document.getElementById("shipping-options").innerHTML = "";
  document.getElementById("checkout-total").innerHTML = "";
  document.getElementById("place-order-btn").disabled = true;
  document.getElementById("checkout-error").textContent = "";
}

async function getShippingQuotes() {
  const zip = document.getElementById("ship-zip").value.trim();
  const err = document.getElementById("checkout-error");
  err.textContent = "";
  if (!zip) { err.textContent = "Enter a destination zip code first."; return; }
  try {
    const options = await api("/api/orders/shipping-quote", { method: "POST", body: { dest_zip: zip } });
    document.getElementById("shipping-options").innerHTML = options.map((o) => `
      <label class="form-inline" style="justify-content:space-between;border:1px solid var(--border);padding:8px;border-radius:8px;margin-bottom:6px;">
        <span><input type="radio" name="ship-service" value="${o.service}" onchange="selectShipping('${o.service}', ${o.cost_cents})" /> ${o.label} (${o.est_business_days})</span>
        <strong>${money(o.cost_cents)}</strong>
      </label>`).join("");
  } catch (e) {
    err.textContent = e.message;
  }
}

function selectShipping(service, costCents) {
  const subtotal = cartCache.reduce((s, i) => s + i.price_cents * i.quantity, 0);
  checkoutQuote = { service, costCents };
  document.getElementById("checkout-total").innerHTML = `Subtotal ${money(subtotal)} + Shipping ${money(costCents)} = <strong>${money(subtotal + costCents)}</strong>`;
  document.getElementById("place-order-btn").disabled = false;
}

async function submitCheckout() {
  const err = document.getElementById("checkout-error");
  err.textContent = "";
  if (!checkoutQuote) { err.textContent = "Select a shipping option first."; return; }
  const body = {
    ship_name: document.getElementById("ship-name").value,
    ship_street: document.getElementById("ship-street").value,
    ship_city: document.getElementById("ship-city").value,
    ship_state: document.getElementById("ship-state").value,
    ship_zip: document.getElementById("ship-zip").value,
    shipping_service: checkoutQuote.service,
  };
  try {
    const order = await api("/api/orders/checkout", { method: "POST", body });
    go("orders");
  } catch (e) {
    err.textContent = e.message;
  }
}

// ---- orders ----
async function loadOrders() {
  const el = document.getElementById("orders-list");
  el.innerHTML = "Loading...";
  try {
    const orders = await api("/api/orders");
    el.innerHTML = orders.map(orderCard).join("") || `<p class="muted">No orders yet.</p>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}

function orderCard(o) {
  const canCancel = o.items.every((i) => i.status === "pending");
  return `<div class="card">
    <div class="form-inline" style="justify-content:space-between">
      <strong>Order #${o.id}</strong> ${badge(o.status)}
      <span class="muted">${new Date(o.created_at).toLocaleString()}</span>
    </div>
    <p class="muted">Ship to: ${escapeHtml(o.ship_name)}, ${escapeHtml(o.ship_street)}, ${escapeHtml(o.ship_city)}, ${o.ship_state} ${o.ship_zip} via ${o.shipping_service}</p>
    <table><tbody>
      ${o.items.map((i) => `<tr><td>${escapeHtml(i.product_name)} x${i.quantity}</td><td>${money(i.unit_price_cents * i.quantity)}</td><td>${badge(i.status)}</td>
        <td>${["fulfilled", "shipped", "delivered"].includes(i.status) ? `<button class="secondary" onclick="requestReturn(${i.id})">Return</button>` : ""}</td></tr>`).join("")}
    </tbody></table>
    <p>Subtotal ${money(o.subtotal_cents)} + Shipping ${money(o.shipping_cost_cents)} = <strong>${money(o.total_cents)}</strong></p>
    ${canCancel ? `<button class="danger" onclick="cancelOrder(${o.id})">Cancel order</button>` : ""}
  </div>`;
}

async function cancelOrder(id) {
  if (!confirm("Cancel this order?")) return;
  try { await api(`/api/orders/${id}/cancel`, { method: "POST" }); loadOrders(); } catch (e) { alert(e.message); }
}
async function requestReturn(orderItemId) {
  const reason = prompt("Reason for return:");
  if (!reason) return;
  try { await api("/api/orders/returns", { method: "POST", body: { order_item_id: orderItemId, reason } }); alert("Return requested."); loadOrders(); } catch (e) { alert(e.message); }
}

// ---- messages ----
async function loadMessages() {
  const el = document.getElementById("messages-list");
  el.innerHTML = "Loading...";
  try {
    const msgs = await api("/api/messages");
    el.innerHTML = msgs.map((m) => `<div class="card">
      <div class="muted">${m.sender_id === currentUser.id ? "You" : "User " + m.sender_id} → ${m.recipient_id === currentUser.id ? "You" : "User " + m.recipient_id}
      ${m.product_id ? ` (product #${m.product_id})` : ""}${m.order_id ? ` (order #${m.order_id})` : ""} · ${new Date(m.created_at).toLocaleString()}</div>
      <div>${escapeHtml(m.body)}</div>
    </div>`).join("") || `<p class="muted">No messages yet.</p>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}

async function sendMessage() {
  const recipient_id = parseInt(document.getElementById("msg-recipient").value, 10);
  const bodyText = document.getElementById("msg-body").value.trim();
  if (!recipient_id || !bodyText) { alert("Enter a recipient user id and a message."); return; }
  try {
    await api("/api/messages", { method: "POST", body: { recipient_id, body: bodyText, product_id: window._pendingMessageProduct || null } });
    window._pendingMessageProduct = null;
    document.getElementById("msg-body").value = "";
    loadMessages();
  } catch (e) { alert(e.message); }
}

// ---- seller dashboard ----
function setSellerTab(tab) {
  document.querySelectorAll("#view-seller .tab-btn").forEach((b) => b.classList.remove("active"));
  event.target.classList.add("active");
  document.querySelectorAll("#view-seller .seller-tab").forEach((d) => (d.style.display = "none"));
  document.getElementById(`seller-${tab}`).style.display = "block";
  if (tab === "store") loadSellerStore();
  if (tab === "products") loadSellerProducts();
  if (tab === "orders") loadSellerOrders();
  if (tab === "returns") loadSellerReturns();
}

async function loadSellerStore() {
  const el = document.getElementById("seller-store");
  try {
    const store = await api("/api/seller/store");
    el.innerHTML = `<div class="card"><h3>${escapeHtml(store.name)}</h3><p>${escapeHtml(store.description)}</p>${badge(store.is_active ? "approved" : "denied")}</div>`;
  } catch (e) {
    el.innerHTML = `<div class="card">
      <p class="muted">You don't have a store yet.</p>
      <div class="form-row"><label>Store name</label><input id="new-store-name" /></div>
      <div class="form-row"><label>Description</label><textarea id="new-store-desc"></textarea></div>
      <button onclick="createStore()">Create store</button>
      <p class="error" id="store-error"></p>
    </div>`;
  }
}
async function createStore() {
  try {
    await api("/api/seller/store", { method: "POST", body: { name: document.getElementById("new-store-name").value, description: document.getElementById("new-store-desc").value } });
    loadSellerStore();
  } catch (e) { document.getElementById("store-error").textContent = e.message; }
}

async function loadSellerProducts() {
  const el = document.getElementById("seller-products");
  el.innerHTML = "Loading...";
  try {
    const products = await api("/api/seller/products");
    el.innerHTML = `<button onclick="showNewProductForm()">+ New product</button><div id="new-product-form"></div>` +
      products.map((p) => `<div class="card">
        <div class="form-inline" style="justify-content:space-between">
          <strong>${escapeHtml(p.name)}</strong> ${badge(p.is_active ? "approved" : "denied")}
        </div>
        <p class="muted">${money(p.price_cents)} · ${p.stock_qty} in stock · ${p.category}</p>
        <div class="image-thumbs">${p.images.map((i) => `<img src="${i}" />`).join("")}</div>
        <div class="form-inline">
          <input type="file" id="img-${p.id}" accept="image/*" />
          <button class="secondary" onclick="uploadImage(${p.id})">Upload image</button>
          <input type="number" id="stock-${p.id}" value="${p.stock_qty}" style="width:80px" />
          <button class="secondary" onclick="updateStock(${p.id})">Update stock</button>
          <button class="danger" onclick="deleteProduct(${p.id})">Delete</button>
        </div>
      </div>`).join("");
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}

function showNewProductForm() {
  document.getElementById("new-product-form").innerHTML = `<div class="card">
    <div class="form-inline">
      <div class="form-row"><label>Name</label><input id="np-name" /></div>
      <div class="form-row"><label>Category</label><input id="np-category" value="general" /></div>
      <div class="form-row"><label>Price (USD)</label><input id="np-price" type="number" step="0.01" /></div>
      <div class="form-row"><label>Stock</label><input id="np-stock" type="number" value="1" /></div>
      <div class="form-row"><label>Weight (oz)</label><input id="np-weight" type="number" value="8" /></div>
      <div class="form-row"><label>L in</label><input id="np-l" type="number" value="6" /></div>
      <div class="form-row"><label>W in</label><input id="np-w" type="number" value="6" /></div>
      <div class="form-row"><label>H in</label><input id="np-h" type="number" value="6" /></div>
    </div>
    <div class="form-row"><label>Description</label><textarea id="np-desc"></textarea></div>
    <button onclick="createProduct()">Create</button>
    <p class="error" id="np-error"></p>
  </div>`;
}
async function createProduct() {
  const body = {
    name: document.getElementById("np-name").value,
    category: document.getElementById("np-category").value,
    description: document.getElementById("np-desc").value,
    price_cents: Math.round(parseFloat(document.getElementById("np-price").value) * 100),
    stock_qty: parseInt(document.getElementById("np-stock").value, 10),
    weight_oz: parseFloat(document.getElementById("np-weight").value),
    length_in: parseFloat(document.getElementById("np-l").value),
    width_in: parseFloat(document.getElementById("np-w").value),
    height_in: parseFloat(document.getElementById("np-h").value),
  };
  try {
    await api("/api/seller/products", { method: "POST", body });
    loadSellerProducts();
  } catch (e) { document.getElementById("np-error").textContent = e.message; }
}
async function updateStock(id) {
  try {
    await api(`/api/seller/products/${id}`, { method: "PATCH", body: { stock_qty: parseInt(document.getElementById(`stock-${id}`).value, 10) } });
    loadSellerProducts();
  } catch (e) { alert(e.message); }
}
async function deleteProduct(id) {
  if (!confirm("Delete this product?")) return;
  try { await api(`/api/seller/products/${id}`, { method: "DELETE" }); loadSellerProducts(); } catch (e) { alert(e.message); }
}
async function uploadImage(id) {
  const fileInput = document.getElementById(`img-${id}`);
  if (!fileInput.files[0]) return alert("Choose an image file first.");
  const form = new FormData();
  form.append("file", fileInput.files[0]);
  try { await api(`/api/seller/products/${id}/images`, { method: "POST", body: form, isForm: true }); loadSellerProducts(); } catch (e) { alert(e.message); }
}

async function loadSellerOrders() {
  const el = document.getElementById("seller-orders");
  el.innerHTML = "Loading...";
  try {
    const items = await api("/api/seller/orders");
    const nextStatus = { pending: "fulfilled", fulfilled: "shipped", shipped: "delivered" };
    el.innerHTML = `<table><thead><tr><th>Item</th><th>Qty</th><th>Status</th><th></th></tr></thead><tbody>` +
      items.map((i) => `<tr><td>${escapeHtml(i.product_name)}</td><td>${i.quantity}</td><td>${badge(i.status)}</td>
        <td>${nextStatus[i.status] ? `<button class="secondary" onclick="advanceItem(${i.id}, '${nextStatus[i.status]}')">Mark ${nextStatus[i.status]}</button>` : ""}</td></tr>`).join("") +
      `</tbody></table>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function advanceItem(id, status) {
  try { await api(`/api/seller/orders/items/${id}`, { method: "PATCH", body: { status } }); loadSellerOrders(); } catch (e) { alert(e.message); }
}

async function loadSellerReturns() {
  const el = document.getElementById("seller-returns");
  el.innerHTML = "Loading...";
  try {
    const returns = await api("/api/seller/returns");
    el.innerHTML = returns.map((r) => `<div class="card">
      <div class="form-inline" style="justify-content:space-between"><strong>Return #${r.id}</strong> ${badge(r.status)}</div>
      <p>${escapeHtml(r.reason)}</p>
      ${r.status === "pending" ? `<button onclick="decideReturn(${r.id}, true)">Approve</button> <button class="danger" onclick="decideReturn(${r.id}, false)">Deny</button>` : ""}
    </div>`).join("") || `<p class="muted">No return requests.</p>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function decideReturn(id, approve) {
  try { await api(`/api/seller/returns/${id}`, { method: "PATCH", body: { approve } }); loadSellerReturns(); } catch (e) { alert(e.message); }
}

// ---- admin dashboard ----
function setAdminTab(tab) {
  document.querySelectorAll("#view-admin .tab-btn").forEach((b) => b.classList.remove("active"));
  event.target.classList.add("active");
  document.querySelectorAll("#view-admin .admin-tab").forEach((d) => (d.style.display = "none"));
  document.getElementById(`admin-${tab}`).style.display = "block";
  ({ analytics: loadAdminAnalytics, users: loadAdminUsers, stores: loadAdminStores, products: loadAdminProducts, orders: loadAdminOrders, settings: loadAdminSettings }[tab])();
}

async function loadAdminAnalytics() {
  const el = document.getElementById("admin-analytics");
  el.innerHTML = "Loading...";
  try {
    const a = await api("/api/admin/analytics");
    el.innerHTML = `<div class="grid">
      ${statTile("Users", a.total_users)}${statTile("Customers", a.total_customers)}${statTile("Sellers", a.total_sellers)}
      ${statTile("Stores", a.total_stores)}${statTile("Products", a.total_products)}${statTile("Orders", a.total_orders)}
      ${statTile("Revenue", money(a.total_revenue_cents))}${statTile("Commission earned", money(a.commission_earned_cents))}
    </div>
    <div class="card"><h3>Orders by status</h3>${Object.entries(a.orders_by_status).map(([k, v]) => `${badge(k)} ${v}`).join(" ")}</div>
    <div class="card"><h3>Top products</h3><table>${a.top_products.map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${p.units_sold} sold</td></tr>`).join("")}</table></div>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
function statTile(label, value) { return `<div class="card"><div class="muted">${label}</div><div style="font-size:1.4rem;font-weight:700">${value}</div></div>`; }

async function loadAdminUsers() {
  const el = document.getElementById("admin-users");
  el.innerHTML = "Loading...";
  try {
    const users = await api("/api/admin/users");
    el.innerHTML = `<table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead><tbody>` +
      users.map((u) => `<tr><td>${escapeHtml(u.name)}</td><td>${escapeHtml(u.email)}</td><td>${u.role}</td><td>${u.is_active ? "Yes" : "No"}</td>
        <td><button class="secondary" onclick="toggleUserActive(${u.id}, ${!u.is_active})">${u.is_active ? "Deactivate" : "Activate"}</button></td></tr>`).join("") +
      `</tbody></table>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function toggleUserActive(id, active) {
  try { await api(`/api/admin/users/${id}`, { method: "PATCH", body: { is_active: active } }); loadAdminUsers(); } catch (e) { alert(e.message); }
}

async function loadAdminStores() {
  const el = document.getElementById("admin-stores");
  el.innerHTML = "Loading...";
  try {
    const stores = await api("/api/admin/stores");
    el.innerHTML = stores.map((s) => `<div class="card form-inline" style="justify-content:space-between">
      <span><strong>${escapeHtml(s.name)}</strong> ${badge(s.is_active ? "approved" : "denied")}</span>
      <button class="secondary" onclick="toggleStoreActive(${s.id}, ${!s.is_active})">${s.is_active ? "Deactivate" : "Activate"}</button>
    </div>`).join("");
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function toggleStoreActive(id, active) {
  try { await api(`/api/admin/stores/${id}`, { method: "PATCH", body: { is_active: active } }); loadAdminStores(); } catch (e) { alert(e.message); }
}

async function loadAdminProducts() {
  const el = document.getElementById("admin-products");
  el.innerHTML = "Loading...";
  try {
    const products = await api("/api/admin/products");
    el.innerHTML = `<table><thead><tr><th>Name</th><th>Store</th><th>Price</th><th>Active</th><th></th></tr></thead><tbody>` +
      products.map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${p.store_id}</td><td>${money(p.price_cents)}</td><td>${p.is_active ? "Yes" : "No"}</td>
        <td>${p.is_active ? `<button class="danger" onclick="deactivateProductAdmin(${p.id})">Deactivate</button>` : ""}</td></tr>`).join("") +
      `</tbody></table>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function deactivateProductAdmin(id) {
  try { await api(`/api/admin/products/${id}/deactivate`, { method: "PATCH" }); loadAdminProducts(); } catch (e) { alert(e.message); }
}

async function loadAdminOrders() {
  const el = document.getElementById("admin-orders");
  el.innerHTML = "Loading...";
  try {
    const orders = await api("/api/admin/orders");
    el.innerHTML = orders.map(orderCard).join("");
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}

async function loadAdminSettings() {
  const el = document.getElementById("admin-settings");
  el.innerHTML = "Loading...";
  try {
    const s = await api("/api/admin/settings");
    el.innerHTML = `<div class="card" style="max-width:400px">
      <div class="form-row"><label>Site name</label><input id="set-name" value="${escapeHtml(s.site_name)}" /></div>
      <div class="form-row"><label>Commission (basis points, 100 = 1%)</label><input id="set-commission" type="number" value="${s.commission_bps}" /></div>
      <div class="form-row"><label><input type="checkbox" id="set-maintenance" ${s.maintenance_mode ? "checked" : ""} /> Maintenance mode</label></div>
      <button onclick="saveSettings()">Save</button>
      <p class="success" id="settings-msg"></p>
    </div>`;
  } catch (e) { el.innerHTML = `<p class="error">${e.message}</p>`; }
}
async function saveSettings() {
  try {
    await api("/api/admin/settings", { method: "PATCH", body: {
      site_name: document.getElementById("set-name").value,
      commission_bps: parseInt(document.getElementById("set-commission").value, 10),
      maintenance_mode: document.getElementById("set-maintenance").checked,
    }});
    document.getElementById("settings-msg").textContent = "Saved.";
  } catch (e) { alert(e.message); }
}

// ---- chatbot ----
function toggleChat() {
  const panel = document.getElementById("chat-panel");
  panel.classList.toggle("open");
  if (panel.classList.contains("open") && document.getElementById("chat-log").children.length === 0) {
    appendChatMsg("assistant", "Hi! I can help with general shopping questions. For anything about a specific product or order, I'll point you to the seller.");
  }
}
function appendChatMsg(role, text) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
async function sendChat(e) {
  e.preventDefault();
  if (!currentUser) { toggleChat(); go("auth"); return false; }
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return false;
  appendChatMsg("user", message);
  input.value = "";
  try {
    const res = await api("/api/chat", { method: "POST", body: { message } });
    appendChatMsg("assistant", res.reply + (res.suggest_contact_seller ? "\n\n(Tip: use \"Message seller\" on the product/order for specifics.)" : ""));
  } catch (err) {
    appendChatMsg("assistant", `Sorry, something went wrong: ${err.message}`);
  }
  return false;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

restoreSession();
