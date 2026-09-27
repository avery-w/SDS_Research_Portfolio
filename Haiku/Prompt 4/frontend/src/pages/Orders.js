import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API_URL}/orders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrders(Array.isArray(response.data) ? response.data : [response.data]);
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
    setLoading(false);
  };

  const handleCancel = async (orderId) => {
    try {
      await axios.post(
        `${API_URL}/orders/${orderId}/cancel`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchOrders();
    } catch (error) {
      console.error('Error cancelling order:', error);
    }
  };

  if (loading) {
    return <div className="container"><p>Loading orders...</p></div>;
  }

  return (
    <div className="container">
      <h1>My Orders</h1>

      {orders.length === 0 ? (
        <p style={{ marginTop: '2rem', color: '#666' }}>
          No orders yet. <a href="/">Start shopping</a>
        </p>
      ) : (
        <div style={{ marginTop: '2rem' }}>
          {orders.map((order) => (
            <div key={order.id} className="card" style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <h3>Order #{order.id}</h3>
                  <p style={{ color: '#666' }}>
                    Status: <span className={`badge badge-${
                      order.status === 'delivered' ? 'success' :
                      order.status === 'shipped' ? 'info' :
                      order.status === 'paid' ? 'warning' :
                      'danger'
                    }`}>{order.status}</span>
                  </p>
                  <p style={{ color: '#666' }}>
                    Created: {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <h2 style={{ color: '#0066cc' }}>
                    ${order.total_amount.toFixed(2)}
                  </h2>
                  {order.tracking_number && (
                    <p>Tracking: {order.tracking_number}</p>
                  )}
                </div>
              </div>

              <h4 style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>Items:</h4>
              <ul style={{ marginLeft: '1.5rem' }}>
                {order.items && order.items.map((item) => (
                  <li key={item.id}>
                    {item.product?.name} x {item.quantity} @ ${item.price_at_purchase.toFixed(2)}
                  </li>
                ))}
              </ul>

              {order.status === 'pending' && (
                <button
                  onClick={() => handleCancel(order.id)}
                  className="button button-secondary"
                  style={{ marginTop: '1rem' }}
                >
                  Cancel Order
                </button>
              )}

              {order.status === 'delivered' && (
                <button
                  className="button button-secondary"
                  style={{ marginTop: '1rem' }}
                >
                  Request Return
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
