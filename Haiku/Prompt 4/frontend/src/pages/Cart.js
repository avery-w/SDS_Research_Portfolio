import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Cart() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchCart();
  }, []);

  const fetchCart = async () => {
    try {
      const response = await axios.get(`${API_URL}/cart`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setItems(response.data);
    } catch (error) {
      console.error('Error fetching cart:', error);
    }
    setLoading(false);
  };

  const handleRemove = async (itemId) => {
    try {
      await axios.delete(`${API_URL}/cart/${itemId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setItems(items.filter((item) => item.id !== itemId));
    } catch (error) {
      console.error('Error removing item:', error);
    }
  };

  const handleUpdateQuantity = async (itemId, newQuantity) => {
    if (newQuantity < 1) return;
    try {
      await axios.put(
        `${API_URL}/cart/${itemId}`,
        { product_id: items.find((i) => i.id === itemId).product.id, quantity: newQuantity },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchCart();
    } catch (error) {
      console.error('Error updating quantity:', error);
    }
  };

  if (loading) {
    return <div className="container"><p>Loading cart...</p></div>;
  }

  const total = items.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  return (
    <div className="container">
      <h1>Shopping Cart</h1>

      {items.length === 0 ? (
        <p style={{ marginTop: '2rem', color: '#666' }}>
          Your cart is empty. <a href="/">Continue shopping</a>
        </p>
      ) : (
        <div>
          <table style={{ marginTop: '2rem' }}>
            <thead>
              <tr>
                <th>Product</th>
                <th>Price</th>
                <th>Quantity</th>
                <th>Total</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.product.name}</td>
                  <td>${item.product.price.toFixed(2)}</td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      max={item.product.quantity_available}
                      value={item.quantity}
                      onChange={(e) =>
                        handleUpdateQuantity(item.id, parseInt(e.target.value))
                      }
                      style={{ maxWidth: '80px' }}
                    />
                  </td>
                  <td>${(item.product.price * item.quantity).toFixed(2)}</td>
                  <td>
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="button button-secondary"
                      style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: '2rem', textAlign: 'right' }}>
            <h2>Total: ${total.toFixed(2)}</h2>
            <button
              onClick={() => navigate('/checkout')}
              className="button"
              style={{ marginTop: '1rem', padding: '1rem 2rem', fontSize: '1.1rem' }}
            >
              Proceed to Checkout
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
