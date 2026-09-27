import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { addressAPI, ordersAPI, shippingAPI } from '../services/api';
import '../App.css';

function Checkout() {
  const [addresses, setAddresses] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState('');
  const [shippingMethod, setShippingMethod] = useState('ground');
  const [paymentMethod, setPaymentMethod] = useState('credit_card');
  const [shippingRates, setShippingRates] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAddresses();
  }, []);

  const fetchAddresses = async () => {
    try {
      const response = await addressAPI.list();
      setAddresses(response.data);
      if (response.data.length > 0) {
        setSelectedAddress(response.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching addresses:', error);
    }
  };

  const handleCheckout = async (e) => {
    e.preventDefault();
    if (!selectedAddress) {
      alert('Please select a delivery address');
      return;
    }

    try {
      setLoading(true);
      await ordersAPI.create({
        delivery_address_id: selectedAddress,
        shipping_method: shippingMethod,
        payment_method: paymentMethod
      });
      navigate('/orders');
    } catch (error) {
      alert('Checkout failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Checkout</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
        <div className="form">
          <h3>Delivery Address</h3>
          {addresses.length === 0 ? (
            <p>No addresses on file. Please add an address.</p>
          ) : (
            <div className="form-group">
              <select
                value={selectedAddress}
                onChange={(e) => setSelectedAddress(e.target.value)}
              >
                {addresses.map(addr => (
                  <option key={addr.id} value={addr.id}>
                    {addr.street}, {addr.city}, {addr.state} {addr.zip_code}
                  </option>
                ))}
              </select>
            </div>
          )}

          <h3 style={{ marginTop: '2rem' }}>Shipping Method</h3>
          <div className="form-group">
            <label>
              <input
                type="radio"
                value="ground"
                checked={shippingMethod === 'ground'}
                onChange={(e) => setShippingMethod(e.target.value)}
              />
              Ground (5 days) - $5.00
            </label>
            <label>
              <input
                type="radio"
                value="express"
                checked={shippingMethod === 'express'}
                onChange={(e) => setShippingMethod(e.target.value)}
              />
              Express (3 days) - $15.00
            </label>
            <label>
              <input
                type="radio"
                value="overnight"
                checked={shippingMethod === 'overnight'}
                onChange={(e) => setShippingMethod(e.target.value)}
              />
              Overnight (1 day) - $25.00
            </label>
          </div>

          <h3 style={{ marginTop: '2rem' }}>Payment Method</h3>
          <div className="form-group">
            <label>
              <input
                type="radio"
                value="credit_card"
                checked={paymentMethod === 'credit_card'}
                onChange={(e) => setPaymentMethod(e.target.value)}
              />
              Credit Card
            </label>
            <label>
              <input
                type="radio"
                value="debit_card"
                checked={paymentMethod === 'debit_card'}
                onChange={(e) => setPaymentMethod(e.target.value)}
              />
              Debit Card
            </label>
          </div>

          <button
            className="button button-success"
            onClick={handleCheckout}
            disabled={loading}
            style={{ width: '100%', marginTop: '2rem' }}
          >
            {loading ? 'Processing...' : 'Complete Order'}
          </button>
        </div>

        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', height: 'fit-content' }}>
          <h3>Order Summary</h3>
          <p style={{ color: '#666' }}>Subtotal: $0.00</p>
          <p style={{ color: '#666' }}>Shipping: $5.00</p>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', borderTop: '1px solid #ddd', paddingTop: '1rem' }}>
            Total: $5.00
          </div>
        </div>
      </div>
    </div>
  );
}

export default Checkout;
