const API = "";
let token = localStorage.getItem("token") || null;
let currentUser = null;

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
  return data;
}

function showSection(name) {
  document.querySelectorAll(".section").forEach((el) => el.classList.add("hidden"));
  const el = document.getElementById("section-" + name);
  if (el) el.classList.remove("hidden");
  if (name === "products") loadProducts();
  if (name === "cart") loadCart();
  if (name === "orders") loadOrders();
  if (name === "seller") loadSeller();
  if (name === "admin") loadAdmin();
}

function updateAuthUI() {
  const area = document.getElementById("auth-area");
  if (token && currentUser) {
    area.innerHTML = `
      <span style="color:var(--muted)">${currentUser.email} (${currentUser.role})</span>
      ${currentUser.role === "seller" ? '<a href="#" onclick="showSection(\'seller\')">Seller</a>' : ""}
      ${currentUser.role === "admin" ? '<a href="#" onclick="showSection(\'admin\')">Admin</a>' : ""}
      <a href="#" onclick="logout()">Logout</a>
    `;
  } else {
    area.innerHTML = `
      <a href="#" onclick="showSection('login')">Login</a>
      <a href="#" onclick="showSection('register')">Register</a>
    `;
  }
}

async function loadMe() {
  if (!token) return;
  try {
    currentUser = await api("/auth/me");
    updateAuthUI();
  } catch {
    token = null;
    localStorage.removeItem("token");
    currentUser = null;
    updateAuthUI();
  }
}

async function doLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || "Login failed");
  token = data.access_token;
  localStorage.setItem("token", token);
  await loadMe();
  showSection("products");
}

async function doRegister(e) {
  e.preventDefault();
  try {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("reg-email").value,
        password: document.getElementById("reg-password").value,
        full_name: document.getElementById("reg-name").value,
        role: document.getElementById("reg-role").value,
      }),
    });
    alert("Account created! Please log in.");
    showSection("login");
  } catch (err) {
    alert(err.message);
  }
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem("token");
  updateAuthUI();
  showSection("login");
}

async function loadProducts() {
  const q = document.getElementById("search-q")?.value || "";
  const list = document.getElementById("product-list");
  list.innerHTML = "Loading…";
  try {
    const products = await api(`/customer/products?q=${encodeURIComponent(q)}`);
    if (!products.length) {
      list.innerHTML = "<p>No products found.</p>";
      return;
    }
    list.innerHTML = products
      .map(
        (p) => `
      <div class="card">
        ${p.image_path ? `<img src="/uploads/${p.image_path}" alt="">` : "<div style='height:160px;background:#111;border-radius:6px'></div>"}
        <h3>${escapeHtml(p.name)}</h3>
        <div class="price">$${p.price.toFixed(2)}</div>
        <div class="meta">Stock: ${p.inventory}</div>
        <p class="meta">${escapeHtml((p.description || "").slice(0, 80))}</p>
        <button class="btn primary sm" onclick="addToCart(${p.id})">Add to Cart</button>
      </div>`
      )
      .join("");
  } catch (err) {
    list.innerHTML = `<p>${err.message}</p>`;
  }
}

async function addToCart(productId) {
  if (!token) return alert("Please log in as a customer first");
  try {
    await api("/customer/cart", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity: 1 }),
    });
    alert("Added to cart");
  } catch (err) {
    alert(err.message);
  }
}

async function loadCart() {
  const list = document.getElementById("cart-list");
  const actions = document.getElementById("cart-actions");
  if (!token) {
    list.innerHTML = "<p>Please log in.</p>";
    actions.classList.add("hidden");
    return;
  }
  try {
    const items = await api("/customer/cart");
    if (!items.length) {
      list.innerHTML = "<p>Cart is empty.</p>";
      actions.classList.add("hidden");
      return;
    }
    let total = 0;
    list.innerHTML = `
      <table>
        <thead><tr><th>Product</th><th>Qty</th><th>Price</th><th></th></tr></thead>
        <tbody>
          ${items
            .map((i) => {
              total += i.product.price * i.quantity;
              return `<tr>
                <td>${escapeHtml(i.product.name)}</td>
                <td>${i.quantity}</td>
                <td>$${(i.product.price * i.quantity).toFixed(2)}</td>
                <td><button class="btn danger sm" onclick="removeCartItem(${i.id})">Remove</button></td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
      <p style="margin-top:0.75rem"><strong>Subtotal: $${total.toFixed(2)}</strong></p>
    `;
    actions.classList.remove("hidden");
  } catch (err) {
    list.innerHTML = `<p>${err.message}</p>`;
  }
}

async function removeCartItem(id) {
  try {
    await api(`/customer/cart/${id}`, { method: "DELETE" });
    loadCart();
  } catch (err) {
    alert(err.message);
  }
}

async function doCheckout() {
  const address = document.getElementById("ship-address").value.trim();
  const zip = document.getElementById("ship-zip").value.trim();
  if (!address || !zip) return alert("Address and ZIP required");
  try {
    // Preview shipping
    const items = await api("/customer/cart");
    let weight = 0, l = 0, w = 0, h = 0;
    items.forEach((i) => {
      weight += i.product.weight_lb * i.quantity;
      l = Math.max(l, i.product.length_in);
      w = Math.max(w, i.product.width_in);
      h = Math.max(h, i.product.height_in);
    });
    const rates = await api("/api/shipping/rates", {
      method: "POST",
      body: JSON.stringify({ dest_zip: zip, weight_lb: weight, length_in: l, width_in: w, height_in: h }),
    });
    document.getElementById("ship-preview").textContent = JSON.stringify(rates, null, 2);

    if (!confirm(`Shipping ≈ $${rates.shipping_cost}. Place order?`)) return;

    const order = await api("/api/checkout", {
      method: "POST",
      body: JSON.stringify({ shipping_address: address, shipping_zip: zip }),
    });
    alert(`Order #${order.id} placed! Total: $${order.total}`);
    loadCart();
    showSection("orders");
  } catch (err) {
    alert(err.message);
  }
}

async function loadOrders() {
  const list = document.getElementById("order-list");
  if (!token) {
    list.innerHTML = "<p>Please log in.</p>";
    return;
  }
  try {
    const orders = await api("/customer/orders");
    if (!orders.length) {
      list.innerHTML = "<p>No orders yet.</p>";
      return;
    }
    list.innerHTML = orders
      .map(
        (o) => `
      <div class="card" style="margin-bottom:1rem">
        <strong>Order #${o.id}</strong> – ${o.status} – $${o.total.toFixed(2)}
        <div class="meta">${new Date(o.created_at).toLocaleString()}</div>
        <div class="meta">Ship to: ${escapeHtml(o.shipping_address)} (${o.shipping_zip})</div>
        ${
          ["pending", "paid"].includes(o.status)
            ? `<button class="btn sm" onclick="cancelOrder(${o.id})">Cancel</button>`
            : ""
        }
        ${
          ["shipped", "delivered"].includes(o.status)
            ? `<button class="btn sm" onclick="returnOrder(${o.id})">Request Return</button>`
            : ""
        }
      </div>`
      )
      .join("");
  } catch (err) {
    list.innerHTML = `<p>${err.message}</p>`;
  }
}

async function cancelOrder(id) {
  try {
    await api(`/customer/orders/${id}/cancel`, { method: "POST" });
    loadOrders();
  } catch (err) {
    alert(err.message);
  }
}

async function returnOrder(id) {
  try {
    await api(`/customer/orders/${id}/return`, { method: "POST" });
    loadOrders();
  } catch (err) {
    alert(err.message);
  }
}

async function sendChat() {
  const input = document.getElementById("chat-msg");
  const msg = input.value.trim();
  if (!msg) return;
  if (!token) return alert("Please log in to use the chat");
  const box = document.getElementById("chat-box");
  box.innerHTML += `<div class="chat-msg user"><span class="bubble">${escapeHtml(msg)}</span></div>`;
  input.value = "";
  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: msg }),
    });
    box.innerHTML += `<div class="chat-msg bot"><span class="bubble">${escapeHtml(data.reply)}</span></div>`;
    box.scrollTop = box.scrollHeight;
  } catch (err) {
    box.innerHTML += `<div class="chat-msg bot"><span class="bubble">Error: ${escapeHtml(err.message)}</span></div>`;
  }
}

async function loadSeller() {
  if (!currentUser || currentUser.role !== "seller") return;
  try {
    const store = await api("/seller/store");
    document.getElementById("seller-info").innerHTML = `
      <p><strong>${escapeHtml(store.name)}</strong> – ${escapeHtml(store.description || "")}</p>
    `;
    const products = await api("/seller/products");
    document.getElementById("seller-products").innerHTML = products
      .map(
        (p) => `
      <div class="card">
        <h3>${escapeHtml(p.name)}</h3>
        <div class="price">$${p.price.toFixed(2)}</div>
        <div class="meta">Stock: ${p.inventory} · Active: ${p.is_active}</div>
      </div>`
      )
      .join("") || "<p>No products yet.</p>";

    const orders = await api("/seller/orders");
    document.getElementById("seller-orders").innerHTML = orders
      .map(
        (o) => `
      <div class="card" style="margin-bottom:0.75rem">
        Order #${o.id} – ${o.status} – $${o.total.toFixed(2)}
        ${
          o.status === "paid"
            ? `<button class="btn sm" onclick="sellerShip(${o.id})">Mark Shipped</button>`
            : ""
        }
      </div>`
      )
      .join("") || "<p>No orders yet.</p>";
  } catch (err) {
    alert(err.message);
  }
}

async function createProduct(e) {
  e.preventDefault();
  const fd = new FormData();
  fd.append("name", document.getElementById("p-name").value);
  fd.append("description", document.getElementById("p-desc").value);
  fd.append("price", document.getElementById("p-price").value);
  fd.append("inventory", document.getElementById("p-inv").value);
  fd.append("weight_lb", document.getElementById("p-weight").value);
  const img = document.getElementById("p-image").files[0];
  if (img) fd.append("image", img);

  const res = await fetch("/seller/products", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || "Failed");
  alert("Product created");
  e.target.reset();
  loadSeller();
}

async function sellerShip(orderId) {
  try {
    await api(`/seller/orders/${orderId}/status?status=shipped`, { method: "PATCH" });
    loadSeller();
  } catch (err) {
    alert(err.message);
  }
}

async function loadAdmin() {
  if (!currentUser || currentUser.role !== "admin") return;
  try {
    const a = await api("/admin/analytics");
    document.getElementById("admin-analytics").innerHTML = `
      <div class="stat"><div class="value">$${a.total_revenue.toFixed(0)}</div><div class="label">Revenue</div></div>
      <div class="stat"><div class="value">${a.order_count}</div><div class="label">Orders</div></div>
      <div class="stat"><div class="value">${a.active_users}</div><div class="label">Users</div></div>
      <div class="stat"><div class="value">${a.active_stores}</div><div class="label">Stores</div></div>
      <div class="stat"><div class="value">${a.active_products}</div><div class="label">Products</div></div>
    `;
    const users = await api("/admin/users");
    document.getElementById("admin-users").innerHTML = `
      <table><thead><tr><th>ID</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead>
      <tbody>
        ${users
          .map(
            (u) => `<tr>
              <td>${u.id}</td><td>${escapeHtml(u.email)}</td><td>${u.role}</td><td>${u.is_active}</td>
              <td>
                ${u.is_active && u.role !== "admin" ? `<button class="btn danger sm" onclick="deactivateUser(${u.id})">Deactivate</button>` : ""}
                ${!u.is_active ? `<button class="btn sm" onclick="activateUser(${u.id})">Activate</button>` : ""}
              </td>
            </tr>`
          )
          .join("")}
      </tbody></table>
    `;
    const orders = await api("/admin/orders");
    document.getElementById("admin-orders").innerHTML = orders
      .map(
        (o) => `<div class="card" style="margin-bottom:0.5rem">
          #${o.id} · ${o.status} · $${o.total.toFixed(2)} · ${new Date(o.created_at).toLocaleDateString()}
        </div>`
      )
      .join("") || "<p>No orders.</p>";
  } catch (err) {
    alert(err.message);
  }
}

async function deactivateUser(id) {
  try {
    await api(`/admin/users/${id}/deactivate`, { method: "PATCH" });
    loadAdmin();
  } catch (err) {
    alert(err.message);
  }
}

async function activateUser(id) {
  try {
    await api(`/admin/users/${id}/activate`, { method: "PATCH" });
    loadAdmin();
  } catch (err) {
    alert(err.message);
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Init
loadMe();
