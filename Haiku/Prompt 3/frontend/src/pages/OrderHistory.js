import React, { useState, useEffect } from 'react';
import { orders } from '../api';
import '../styles/Common.css';

function OrderHistory() {
  const [orderList, setOrderList] = useState([]);

  useEffect(() => {
    orders.list().then((res) => setOrderList(res.data)).catch(() => alert('Failed to load orders'));
  }, []);

  return (
    <div className="container">
      <h1>Order History</h1>
      {orderList.map((order) => (
        <div key={order.id} className="order-card">
          <div className="order-header">
            <div>
              <p><strong>{order.order_number}</strong></p>
              <p>Created: {new Date(order.created_at).toLocaleDateString()}</p>
            </div>
            <span className={`order-status status-${order.status}`}>{order.status}</span>
          </div>
          <p>Total: ${order.total_price}</p>
          {order.tracking_number && <p>Tracking: {order.tracking_number}</p>}
          <h4>Items:</h4>
          {order.items?.map((item) => (
            <p key={item.id}>{item.product?.name} x{item.quantity}</p>
          ))}
        </div>
      ))}
    </div>
  );
}

export default OrderHistory;
