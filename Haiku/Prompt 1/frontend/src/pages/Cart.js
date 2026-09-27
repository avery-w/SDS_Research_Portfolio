import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cartAPI } from '../services/api';
import '../App.css';

function Cart() {
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCart();
  }, []);

  const fetchCart = async () => {
    try {
      const response = await cartAPI.get();
      setCart(response.data);
    } catch (error) {
      console.error('Error fetching cart:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveItem = async (itemId) => {
    try {
      await cartAPI.removeItem(itemId);
      fetchCart();
    } catch (error) {
      console.error('Error removing item:', error);
    }
  };

  const handleCheckout = () => {
    navigate('/checkout');
  };

  if (loading) return <div className="loading">Loading cart...</div>;

  const total = cart?.items?.reduce((sum, item) => sum + (item.product.price * item.quantity), 0) || 0;

  return (
    <div className="container">
      <h1 className="page-title">Shopping Cart</h1>

      {!cart?.items || cart.items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', backgroundColor: 'white', borderRadius: '8px' }}>
          <p>Your cart is empty</p>
        </div>
      ) : (
        <>
          <div style={{ backgroundColor: 'white', borderRadius: '8px', overflow: 'hidden', marginBottom: '2rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Quantity</th>
                  <th>Subtotal</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {cart.items.map(item => (
                  <tr key={item.id}>
                    <td>{item.product.name}</td>
                    <td>${item.product.price}</td>
                    <td>{item.quantity}</td>
                    <td>${(item.product.price * item.quantity).toFixed(2)}</td>
                    <td>
                      <button
                        className="button button-danger"
                        onClick={() => handleRemoveItem(item.id)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '2rem' }}>
            <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', minWidth: '300px' }}>
              <h3 style={{ marginBottom: '1rem' }}>Order Summary</h3>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span>Subtotal:</span>
                <span>${total.toFixed(2)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <span>Shipping:</span>
                <span>$5.00</span>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #ddd', paddingTop: '1rem' }}>
                <span>Total:</span>
                <span>${(total + 5).toFixed(2)}</span>
              </div>
              <button
                className="button button-success"
                onClick={handleCheckout}
                style={{ width: '100%', marginTop: '1rem' }}
              >
                Proceed to Checkout
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Cart;
