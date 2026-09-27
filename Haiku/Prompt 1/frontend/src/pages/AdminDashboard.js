import React, { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import '../App.css';

function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [returns, setReturns] = useState([]);

  useEffect(() => {
    if (activeTab === 'dashboard') fetchDashboard();
    else if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'orders') fetchOrders();
    else if (activeTab === 'returns') fetchReturns();
  }, [activeTab]);

  const fetchDashboard = async () => {
    try {
      const res = await adminAPI.getDashboard();
      setDashboard(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await adminAPI.listUsers();
      setUsers(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await adminAPI.listOrders();
      setOrders(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchReturns = async () => {
    try {
      const res = await adminAPI.listReturns();
      setReturns(res.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleDeactivateUser = async (userId) => {
    if (!window.confirm('Deactivate user?')) return;
    try {
      await adminAPI.deactivateUser(userId);
      fetchUsers();
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleApproveReturn = async (returnId) => {
    try {
      await adminAPI.approveReturn(returnId);
      fetchReturns();
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleProcessRefund = async (returnId) => {
    try {
      await adminAPI.processRefund(returnId);
      fetchReturns();
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Admin Dashboard</h1>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', borderBottom: '2px solid #ddd', overflowX: 'auto' }}>
        {['dashboard', 'users', 'orders', 'returns'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              backgroundColor: activeTab === tab ? '#2196F3' : 'transparent',
              color: activeTab === tab ? 'white' : '#666',
              padding: '0.75rem 1rem',
              border: 'none',
              cursor: 'pointer',
              textTransform: 'capitalize'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div style={{ backgroundColor: '#e3f2fd', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Users</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#2196F3' }}>{dashboard.total_users}</p>
          </div>
          <div style={{ backgroundColor: '#e8f5e9', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Sellers</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#4CAF50' }}>{dashboard.total_sellers}</p>
          </div>
          <div style={{ backgroundColor: '#fff3e0', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Orders</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ff9800' }}>{dashboard.total_orders}</p>
          </div>
          <div style={{ backgroundColor: '#fce4ec', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Revenue</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#e91e63' }}>${dashboard.total_revenue}</p>
          </div>
          <div style={{ backgroundColor: '#f3e5f5', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Pending Orders</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#9c27b0' }}>{dashboard.pending_orders}</p>
          </div>
          <div style={{ backgroundColor: '#e0f2f1', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Pending Returns</h4>
            <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#009688' }}>{dashboard.pending_returns}</p>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
          <h3>Users</h3>
          {users.length === 0 ? (
            <p>No users</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>{user.first_name} {user.last_name}</td>
                    <td><span className="role">{user.role}</span></td>
                    <td>{user.is_active ? 'Active' : 'Inactive'}</td>
                    <td>
                      {user.is_active && (
                        <button
                          className="button button-danger"
                          onClick={() => handleDeactivateUser(user.id)}
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'orders' && (
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
          <h3>Orders</h3>
          {orders.length === 0 ? (
            <p>No orders</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr key={order.id}>
                    <td>#{order.id}</td>
                    <td>User {order.customer_id}</td>
                    <td><span className="role">{order.status}</span></td>
                    <td>${order.total_amount}</td>
                    <td>{new Date(order.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'returns' && (
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
          <h3>Returns</h3>
          {returns.length === 0 ? (
            <p>No returns</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Order</th>
                  <th>Status</th>
                  <th>Amount</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {returns.map(ret => (
                  <tr key={ret.id}>
                    <td>#{ret.id}</td>
                    <td>#{ret.order_id}</td>
                    <td><span className="role">{ret.status}</span></td>
                    <td>${ret.refund_amount}</td>
                    <td>
                      {ret.status === 'INITIATED' && (
                        <>
                          <button
                            className="button button-success"
                            onClick={() => handleApproveReturn(ret.id)}
                          >
                            Approve
                          </button>
                          <button
                            className="button"
                            onClick={() => handleProcessRefund(ret.id)}
                            style={{ marginLeft: '0.5rem' }}
                          >
                            Refund
                          </button>
                        </>
                      )}
                    </td>
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

export default AdminDashboard;
