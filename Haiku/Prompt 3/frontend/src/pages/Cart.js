import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cart } from '../api';
import '../styles/Common.css';

function Cart() {
  const [cartData, setCartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCart();
  }, []);

  const fetchCart = async () => {
    try {
      const response = await cart.get();
      setCartData(response.data);
    } catch (err) {
      console.error('Failed to load cart');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (productId) => {
    await cart.removeItem(productId);
    fetchCart();
  };

  const handleCheckout = () => {
    navigate('/checkout');
  };

  if (loading) return <div className="container">Loading...</div>;
  if (!cartData?.items?.length) return <div className="container"><p>Your cart is empty</p></div>;

  return (
    <div className="container">
      <h1>Shopping Cart</h1>
      <div className="cart-items">
        {cartData.items.map((item) => (
          <div key={item.id} className="cart-item">
            <div className="item-info">
              <h3>{item.product.name}</h3>
              <p>Quantity: {item.quantity}</p>
              <p>${item.product.price} each</p>
            </div>
            <button onClick={() => handleRemove(item.product_id)}>Remove</button>
          </div>
        ))}
      </div>
      <div className="cart-summary">
        <h2>Total: ${cartData.total_price}</h2>
        <button className="checkout-btn" onClick={handleCheckout}>Proceed to Checkout</button>
      </div>
    </div>
  );
}

export default Cart;
