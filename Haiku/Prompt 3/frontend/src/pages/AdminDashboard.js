import React, { useState, useEffect } from 'react';
import api from '../api';
import '../styles/Common.css';

function AdminDashboard() {
  const [stats, setStats] = useState({ totalUsers: 0, totalOrders: 0, totalRevenue: 0 });
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    api.get('/users/').then((res) => setUsers(res.data.results || res.data)).catch(() => {});
    api.get('/orders/').then((res) => setOrders(res.data.results || res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const totalRevenue = orders.reduce((sum, order) => sum + parseFloat(order.total_price || 0), 0);
    setStats({ totalUsers: users.length, totalOrders: orders.length, totalRevenue });
  }, [users, orders]);

  const handleDeactivateUser = async (userId) => {
    try {
      await api.patch(`/profiles/${userId}/`, { is_active: false });
      alert('User deactivated');
      const res = await api.get('/users/');
      setUsers(res.data.results || res.data);
    } catch (err) {
      alert('Failed to deactivate user');
    }
  };

  return (
    <div className="container">
      <h1>Admin Dashboard</h1>

      <section style={{ marginBottom: '2rem' }}>
        <h2>Platform Statistics</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
            <p>Total Users</p>
            <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.totalUsers}</p>
          </div>
          <div style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
            <p>Total Orders</p>
            <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.totalOrders}</p>
          </div>
          <div style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
            <p>Total Revenue</p>
            <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>${stats.totalRevenue.toFixed(2)}</p>
          </div>
        </div>
      </section>

      <section>
        <h2>Users</h2>
        {users.map((user) => (
          <div key={user.id} className="order-card">
            <p><strong>{user.email}</strong> - {user.first_name} {user.last_name}</p>
            <button onClick={() => handleDeactivateUser(user.id)}>Deactivate</button>
          </div>
        ))}
      </section>

      <section>
        <h2>Recent Orders</h2>
        {orders.map((order) => (
          <div key={order.id} className="order-card">
            <p><strong>{order.order_number}</strong> - {order.status}</p>
            <p>Customer: {order.customer?.email}</p>
            <p>Total: ${order.total_price}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export default AdminDashboard;
