import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function SellerDashboard() {
  const [stores, setStores] = useState([]);
  const [orders, setOrders] = useState([]);
  const [newStore, setNewStore] = useState({ name: '', description: '' });
  const [activeTab, setActiveTab] = useState('stores');
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const storesRes = await axios.get(`${API_URL}/stores`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStores(storesRes.data);

      const ordersRes = await axios.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrders(Array.isArray(ordersRes.data) ? ordersRes.data : []);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleCreateStore = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/stores`, newStore, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewStore({ name: '', description: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating store:', error);
    }
  };

  return (
    <div className="container">
      <h1>Seller Dashboard</h1>

      <div style={{ marginBottom: '2rem' }}>
        <button
          onClick={() => setActiveTab('stores')}
          style={{
            marginRight: '1rem',
            background: activeTab === 'stores' ? '#0066cc' : '#ddd',
            color: activeTab === 'stores' ? 'white' : '#333',
            border: 'none',
            padding: '0.75rem 1.5rem',
            cursor: 'pointer',
            borderRadius: '4px'
          }}
        >
          My Stores
        </button>
        <button
          onClick={() => setActiveTab('orders')}
          style={{
            background: activeTab === 'orders' ? '#0066cc' : '#ddd',
            color: activeTab === 'orders' ? 'white' : '#333',
            border: 'none',
            padding: '0.75rem 1.5rem',
            cursor: 'pointer',
            borderRadius: '4px'
          }}
        >
          Orders
        </button>
      </div>

      {activeTab === 'stores' && (
        <div>
          <h2>Create New Store</h2>
          <form onSubmit={handleCreateStore} style={{ maxWidth: '500px', marginBottom: '2rem' }}>
            <div className="form-group">
              <label>Store Name</label>
              <input
                type="text"
                value={newStore.name}
                onChange={(e) => setNewStore({ ...newStore, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                value={newStore.description}
                onChange={(e) => setNewStore({ ...newStore, description: e.target.value })}
                required
              />
            </div>
            <button type="submit" className="button">Create Store</button>
          </form>

          <h2>Your Stores</h2>
          <div className="grid">
            {stores.map((store) => (
              <div key={store.id} className="card">
                <div className="card-title">{store.name}</div>
                <p>{store.description}</p>
                <p style={{ marginTop: '1rem', color: '#999' }}>
                  {store.is_active ? (
                    <span className="badge badge-success">Active</span>
                  ) : (
                    <span className="badge badge-danger">Inactive</span>
                  )}
                </p>
              </div>
            ))}
          </div>

          {stores.length === 0 && <p>No stores yet. Create one above!</p>}
        </div>
      )}

      {activeTab === 'orders' && (
        <div>
          <h2>Your Orders</h2>
          {orders.length === 0 ? (
            <p>No orders yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Customer</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>#{order.id}</td>
                    <td>Customer {order.customer_id}</td>
                    <td>${order.total_amount.toFixed(2)}</td>
                    <td>
                      <span className={`badge badge-${
                        order.status === 'delivered' ? 'success' : 'warning'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td>{new Date(order.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
