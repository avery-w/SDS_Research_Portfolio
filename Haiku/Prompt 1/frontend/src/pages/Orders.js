import React, { useState, useEffect } from 'react';
import { ordersAPI } from '../services/api';
import '../App.css';

function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await ordersAPI.list();
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (orderId) => {
    if (!window.confirm('Are you sure you want to cancel this order?')) return;
    try {
      await ordersAPI.cancel(orderId);
      fetchOrders();
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) return <div className="loading">Loading orders...</div>;

  return (
    <div className="container">
      <h1 className="page-title">My Orders</h1>

      {orders.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <p>No orders yet</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {orders.map(order => (
            <div key={order.id} style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div>
                  <h3>Order #{order.id}</h3>
                  <p style={{ color: '#666' }}>
                    {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className="role">{order.status}</span>
                  <p style={{ fontSize: '1.2rem', fontWeight: 'bold', marginTop: '0.5rem' }}>
                    ${order.total_amount}
                  </p>
                </div>
              </div>
              <table style={{ width: '100%', marginBottom: '1rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #ddd' }}>
                    <th style={{ textAlign: 'left' }}>Product</th>
                    <th>Qty</th>
                    <th>Price</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map(item => (
                    <tr key={item.id} style={{ borderBottom: '1px solid #eee' }}>
                      <td>Product {item.product_id}</td>
                      <td>{item.quantity}</td>
                      <td>${item.price_at_purchase}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {order.status === 'PENDING' && (
                <button
                  className="button button-danger"
                  onClick={() => handleCancel(order.id)}
                >
                  Cancel Order
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Orders;
