import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/token/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', response.data.access);
          api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
          return api(originalRequest);
        } catch (err) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export const auth = {
  login: (email, password) => api.post('/token/', { username: email, password }),
  register: (email, first_name, last_name, password, password2, role) =>
    api.post('/users/register/', { email, first_name, last_name, password, password2, role }),
};

export const products = {
  list: (params) => api.get('/products/', { params }),
  detail: (id) => api.get(`/products/${id}/`),
  search: (query) => api.get('/products/', { params: { search: query } }),
  myProducts: () => api.get('/products/my_products/'),
  create: (data) => api.post('/products/', data),
  update: (id, data) => api.patch(`/products/${id}/`, data),
};

export const cart = {
  get: () => api.get('/cart/my_cart/'),
  addItem: (productId, quantity) => api.post('/cart/add_item/', { product_id: productId, quantity }),
  removeItem: (productId) => api.post('/cart/remove_item/', { product_id: productId }),
};

export const orders = {
  list: () => api.get('/orders/my_orders/'),
  checkout: (shippingInfo, billingInfo, paymentMethod) =>
    api.post('/orders/checkout/', { shipping_info: shippingInfo, billing_info: billingInfo, payment_method: paymentMethod }),
  detail: (id) => api.get(`/orders/${id}/`),
};

export const messages = {
  list: () => api.get('/messages/inbox/'),
  send: (recipientId, subject, content, productId) =>
    api.post('/messages/send_message/', { recipient_id: recipientId, subject, content, product_id: productId }),
  markAsRead: (messageId) => api.post('/messages/mark_as_read/', { message_id: messageId }),
};

export const chatbot = {
  chat: (message, productId) => api.post('/chatbot/chat/', { message, product_id: productId }),
};

export const stores = {
  list: () => api.get('/stores/'),
  myStore: () => api.get('/stores/my_store/'),
};

export const reviews = {
  createReview: (productId, rating, title, content) =>
    api.post('/reviews/create_review/', { product_id: productId, rating, title, content }),
};

export default api;
