import React, { useState, useEffect, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '../App';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState('');
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const response = await axios.get(`${API_URL}/products/${id}`);
      setProduct(response.data);
    } catch (error) {
      setMessage('Product not found');
    }
  };

  const handleAddToCart = async () => {
    if (!user) {
      navigate('/login');
      return;
    }

    try {
      await axios.post(
        `${API_URL}/cart`,
        { product_id: parseInt(id), quantity },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessage('Added to cart!');
      setTimeout(() => navigate('/cart'), 1000);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Error adding to cart');
    }
  };

  if (!product) {
    return <div className="container"><p>Loading...</p></div>;
  }

  return (
    <div className="container">
      <div style={{ maxWidth: '800px' }}>
        <h1>{product.name}</h1>
        {message && (
          <div className={message.includes('Error') ? 'error' : 'success'}>
            {message}
          </div>
        )}

        <p style={{ color: '#666', marginTop: '1rem' }}>{product.description}</p>
        <div className="card-price">${product.price.toFixed(2)}</div>

        <div style={{ marginTop: '2rem' }}>
          <p style={{ marginBottom: '1rem' }}>
            {product.quantity_available > 0 ? (
              <span style={{ color: '#28a745', fontWeight: 'bold' }}>
                In Stock ({product.quantity_available} available)
              </span>
            ) : (
              <span style={{ color: '#dc3545', fontWeight: 'bold' }}>Out of Stock</span>
            )}
          </p>

          {product.quantity_available > 0 && user && user.role === 'customer' && (
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="quantity">Quantity:</label>
                <input
                  id="quantity"
                  type="number"
                  min="1"
                  max={product.quantity_available}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ maxWidth: '100px' }}
                />
              </div>
              <button onClick={handleAddToCart} className="button">
                Add to Cart
              </button>
            </div>
          )}

          {!user && (
            <button onClick={() => navigate('/login')} className="button">
              Login to Buy
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
