import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '../App';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Checkout() {
  const { user } = useContext(AuthContext);
  const [step, setStep] = useState(1);
  const [addresses, setAddresses] = useState(user?.addresses || []);
  const [selectedAddressId, setSelectedAddressId] = useState(
    addresses[0]?.id || null
  );
  const [newAddress, setNewAddress] = useState({
    street: '',
    city: '',
    state: '',
    zip_code: '',
    country: 'US'
  });
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const handleAddressSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(
        `${API_URL}/addresses`,
        newAddress,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAddresses([...addresses, response.data]);
      setSelectedAddressId(response.data.id);
      setNewAddress({
        street: '',
        city: '',
        state: '',
        zip_code: '',
        country: 'US'
      });
      setStep(2);
    } catch (error) {
      setMessage('Error saving address');
    }
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    try {
      const orderResponse = await axios.post(
        `${API_URL}/checkout/create-order`,
        { shipping_address_id: selectedAddressId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const orderId = Array.isArray(orderResponse.data)
        ? orderResponse.data[0].id
        : orderResponse.data.id;

      const paymentResponse = await axios.post(
        `${API_URL}/checkout/process-payment`,
        { order_id: orderId, payment_method_id: 'pm_test' },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessage('Order placed successfully!');
      setTimeout(() => navigate('/orders'), 2000);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Payment failed');
    }
  };

  if (step === 1) {
    return (
      <div className="container">
        <h1>Shipping Address</h1>
        {message && (
          <div className={message.includes('Error') ? 'error' : 'success'}>
            {message}
          </div>
        )}

        {addresses.length > 0 && (
          <div style={{ marginBottom: '2rem' }}>
            <h3>Select Existing Address</h3>
            <div>
              {addresses.map((addr) => (
                <label key={addr.id} style={{ display: 'block', margin: '0.5rem 0' }}>
                  <input
                    type="radio"
                    name="address"
                    value={addr.id}
                    checked={selectedAddressId === addr.id}
                    onChange={(e) => setSelectedAddressId(parseInt(e.target.value))}
                  />
                  {addr.street}, {addr.city}, {addr.state} {addr.zip_code}
                </label>
              ))}
            </div>
            <button
              onClick={() => setStep(2)}
              className="button"
              style={{ marginTop: '1rem' }}
            >
              Continue with Selected Address
            </button>
          </div>
        )}

        <h3>{addresses.length > 0 ? 'Or add a new address' : 'Add Shipping Address'}</h3>
        <form onSubmit={handleAddressSubmit} style={{ maxWidth: '500px' }}>
          <div className="form-group">
            <label>Street Address</label>
            <input
              type="text"
              value={newAddress.street}
              onChange={(e) =>
                setNewAddress({ ...newAddress, street: e.target.value })
              }
              required
            />
          </div>
          <div className="form-group">
            <label>City</label>
            <input
              type="text"
              value={newAddress.city}
              onChange={(e) => setNewAddress({ ...newAddress, city: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label>State</label>
            <input
              type="text"
              value={newAddress.state}
              onChange={(e) =>
                setNewAddress({ ...newAddress, state: e.target.value })
              }
              required
            />
          </div>
          <div className="form-group">
            <label>Zip Code</label>
            <input
              type="text"
              value={newAddress.zip_code}
              onChange={(e) =>
                setNewAddress({ ...newAddress, zip_code: e.target.value })
              }
              required
            />
          </div>
          <button type="submit" className="button">
            Continue with New Address
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Payment</h1>
      {message && (
        <div className={message.includes('successfully') ? 'success' : 'error'}>
          {message}
        </div>
      )}
      <form onSubmit={handlePayment} style={{ maxWidth: '500px' }}>
        <div className="form-group">
          <label>Payment Method</label>
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
          >
            <option value="card">Credit Card</option>
            <option value="paypal">PayPal</option>
          </select>
        </div>
        <p style={{ marginTop: '1rem', color: '#666' }}>
          This is a demo. Use card: 4242 4242 4242 4242
        </p>
        <button type="submit" className="button" style={{ marginTop: '1rem' }}>
          Place Order
        </button>
      </form>
    </div>
  );
}
