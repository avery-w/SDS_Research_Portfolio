import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState({
    sales: {},
    users: {},
    products: {}
  });
  const [activeTab, setActiveTab] = useState('analytics');
  const [users, setUsers] = useState([]);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchAnalytics();
    fetchUsers();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [salesRes, usersRes, productsRes] = await Promise.all([
        axios.get(`${API_URL}/admin/analytics/sales`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/admin/analytics/users`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/admin/analytics/products`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setAnalytics({
        sales: salesRes.data,
        users: usersRes.data,
        products: productsRes.data
      });
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  return (
    <div className="container">
      <h1>Admin Dashboard</h1>

      <div style={{ marginBottom: '2rem' }}>
        <button
          onClick={() => setActiveTab('analytics')}
          style={{
            marginRight: '1rem',
            background: activeTab === 'analytics' ? '#0066cc' : '#ddd',
            color: activeTab === 'analytics' ? 'white' : '#333',
            border: 'none',
            padding: '0.75rem 1.5rem',
            cursor: 'pointer',
            borderRadius: '4px'
          }}
        >
          Analytics
        </button>
        <button
          onClick={() => setActiveTab('users')}
          style={{
            background: activeTab === 'users' ? '#0066cc' : '#ddd',
            color: activeTab === 'users' ? 'white' : '#333',
            border: 'none',
            padding: '0.75rem 1.5rem',
            cursor: 'pointer',
            borderRadius: '4px'
          }}
        >
          Users
        </button>
      </div>

      {activeTab === 'analytics' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
            <div className="card">
              <h3>Sales</h3>
              <p style={{ fontSize: '2rem', color: '#0066cc', fontWeight: 'bold' }}>
                ${analytics.sales.total_revenue?.toFixed(2) || '0.00'}
              </p>
              <p style={{ color: '#666' }}>Total Revenue</p>
            </div>
            <div className="card">
              <h3>Orders</h3>
              <p style={{ fontSize: '2rem', color: '#0066cc', fontWeight: 'bold' }}>
                {analytics.sales.total_orders || 0}
              </p>
              <p style={{ color: '#666' }}>Total Orders</p>
            </div>
            <div className="card">
              <h3>Users</h3>
              <p style={{ fontSize: '2rem', color: '#0066cc', fontWeight: 'bold' }}>
                {analytics.users.total_users || 0}
              </p>
              <p style={{ color: '#666' }}>Total Users</p>
            </div>
            <div className="card">
              <h3>Products</h3>
              <p style={{ fontSize: '2rem', color: '#0066cc', fontWeight: 'bold' }}>
                {analytics.products.total_products || 0}
              </p>
              <p style={{ color: '#666' }}>Total Products</p>
            </div>
          </div>

          <h2>Breakdown</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            <div className="card">
              <h3>Sales Summary</h3>
              <p>Paid Orders: {analytics.sales.paid_orders}</p>
              <p>Pending Orders: {analytics.sales.pending_orders}</p>
            </div>
            <div className="card">
              <h3>User Summary</h3>
              <p>Customers: {analytics.users.customers}</p>
              <p>Sellers: {analytics.users.sellers}</p>
              <p>Active Users: {analytics.users.active_users}</p>
            </div>
            <div className="card">
              <h3>Inventory</h3>
              <p>Active Products: {analytics.products.active_products}</p>
              <p>Total Inventory: {analytics.products.total_inventory} units</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div>
          <h2>User Management</h2>
          <table style={{ marginTop: '1.5rem' }}>
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.email}</td>
                  <td>{user.full_name}</td>
                  <td>
                    <span className={`badge badge-${
                      user.role === 'admin' ? 'danger' :
                      user.role === 'seller' ? 'info' :
                      'success'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
