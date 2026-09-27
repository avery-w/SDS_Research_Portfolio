import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { orders } from '../api';
import '../styles/Common.css';

function Checkout() {
  const [shippingAddress, setShippingAddress] = useState('');
  const [shippingCity, setShippingCity] = useState('');
  const [shippingState, setShippingState] = useState('');
  const [shippingZip, setShippingZip] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('card');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const shippingInfo = { address: shippingAddress, city: shippingCity, state: shippingState, zip: shippingZip, country: 'USA' };
      const response = await orders.checkout(shippingInfo, shippingInfo, paymentMethod);
      navigate(`/orders`);
    } catch (err) {
      alert('Checkout failed');
    }
  };

  return (
    <div className="container">
      <h1>Checkout</h1>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Shipping Address</legend>
          <div className="form-group">
            <label>Address</label>
            <input type="text" value={shippingAddress} onChange={(e) => setShippingAddress(e.target.value)} required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>City</label>
              <input type="text" value={shippingCity} onChange={(e) => setShippingCity(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>State</label>
              <input type="text" value={shippingState} onChange={(e) => setShippingState(e.target.value)} required />
            </div>
          </div>
          <div className="form-group">
            <label>ZIP Code</label>
            <input type="text" value={shippingZip} onChange={(e) => setShippingZip(e.target.value)} required />
          </div>
        </fieldset>

        <fieldset>
          <legend>Payment Method</legend>
          <div className="form-group">
            <label>
              <input type="radio" value="card" checked={paymentMethod === 'card'} onChange={(e) => setPaymentMethod(e.target.value)} />
              Credit Card
            </label>
          </div>
        </fieldset>

        <button type="submit" className="checkout-btn">Place Order</button>
      </form>
    </div>
  );
}

export default Checkout;
