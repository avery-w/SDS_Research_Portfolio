import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  register: (userData) => api.post('/auth/register', userData),
  login: (email, password) => api.post('/auth/login', { email, password }),
};

export const productsAPI = {
  list: (params = {}) => api.get('/products', { params }),
  get: (id) => api.get(`/products/${id}`),
  search: (query) => api.get('/products', { params: { search: query } }),
  getReviews: (productId) => api.get(`/products/${productId}/reviews`),
  addReview: (productId, reviewData) => api.post(`/products/${productId}/reviews`, reviewData),
  getCategories: () => api.get('/products/categories/all'),
};

export const cartAPI = {
  get: () => api.get('/customers/cart'),
  addItem: (itemData) => api.post('/customers/cart/items', itemData),
  removeItem: (itemId) => api.delete(`/customers/cart/items/${itemId}`),
};

export const ordersAPI = {
  list: () => api.get('/customers/orders'),
  get: (id) => api.get(`/customers/orders/${id}`),
  create: (orderData) => api.post('/customers/checkout', orderData),
  cancel: (id) => api.post(`/customers/orders/${id}/cancel`),
};

export const addressAPI = {
  list: () => api.get('/customers/addresses'),
  create: (addressData) => api.post('/customers/addresses', addressData),
};

export const returnsAPI = {
  list: () => api.get('/customers/returns'),
  request: (returnData) => api.post('/customers/returns', returnData),
};

export const messagesAPI = {
  list: () => api.get('/customers/messages'),
  send: (messageData) => api.post('/customers/messages', messageData),
};

export const sellerAPI = {
  getStore: () => api.get('/sellers/store'),
  createStore: (storeData) => api.post('/sellers/store', storeData),
  updateStore: (storeData) => api.put('/sellers/store', storeData),
  listProducts: () => api.get('/sellers/products'),
  createProduct: (productData) => api.post('/sellers/products', productData),
  updateProduct: (id, productData) => api.put(`/sellers/products/${id}`, productData),
  deleteProduct: (id) => api.delete(`/sellers/products/${id}`),
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/sellers/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getOrders: () => api.get('/sellers/orders'),
  updateOrderStatus: (orderId, status) => api.put(`/sellers/orders/${orderId}/status`, { new_status: status }),
  getAnalytics: () => api.get('/sellers/analytics'),
};

export const adminAPI = {
  listUsers: (params = {}) => api.get('/admin/users', { params }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  deactivateUser: (id) => api.post(`/admin/users/${id}/deactivate`),
  activateUser: (id) => api.post(`/admin/users/${id}/activate`),
  listStores: () => api.get('/admin/stores'),
  deactivateStore: (id) => api.post(`/admin/stores/${id}/deactivate`),
  listOrders: (params = {}) => api.get('/admin/orders', { params }),
  updateOrderStatus: (id, status) => api.put(`/admin/orders/${id}/status`, { new_status: status }),
  listReturns: (params = {}) => api.get('/admin/returns', { params }),
  approveReturn: (id) => api.post(`/admin/returns/${id}/approve`),
  processRefund: (id) => api.post(`/admin/returns/${id}/refund`),
  getAnalytics: () => api.get('/admin/analytics'),
  getDashboard: () => api.get('/admin/dashboard'),
};

export const chatbotAPI = {
  query: (queryText) => api.post('/integrations/chatbot/query', { query: queryText }),
  getHistory: () => api.get('/integrations/chatbot/history'),
};

export const shippingAPI = {
  getRates: (destination_zip, weight, service_type = 'ground') =>
    api.post('/integrations/shipping/rates', { destination_zip, weight, service_type }),
  estimateShipping: (destination_zip, weight = 1.0) =>
    api.get('/integrations/shipping/estimate', { params: { destination_zip, weight } }),
};

export default api;
