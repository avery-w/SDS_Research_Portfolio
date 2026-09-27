import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { productsAPI, cartAPI } from '../services/api';
import '../App.css';

function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProduct();
    fetchReviews();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const response = await productsAPI.get(id);
      setProduct(response.data);
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const response = await productsAPI.getReviews(id);
      setReviews(response.data);
    } catch (error) {
      console.error('Error fetching reviews:', error);
    }
  };

  const handleAddToCart = async () => {
    try {
      await cartAPI.addItem({ product_id: id, quantity });
      alert('Added to cart');
    } catch (error) {
      alert('Error adding to cart');
    }
  };

  if (loading) return <div className="loading">Loading product...</div>;
  if (!product) return <div className="loading">Product not found</div>;

  return (
    <div className="container">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', backgroundColor: 'white', padding: '2rem', borderRadius: '8px' }}>
        <div>
          <div className="card-image" style={{ height: '400px' }}>[Product Image]</div>
        </div>
        <div>
          <h1 style={{ marginBottom: '1rem' }}>{product.name}</h1>
          <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#2196F3', marginBottom: '1rem' }}>
            ${product.price}
          </p>
          <p style={{ color: '#666', marginBottom: '1rem', lineHeight: '1.6' }}>
            {product.description}
          </p>
          <p style={{ marginBottom: '1rem' }}>
            <strong>Category:</strong> {product.category}
          </p>
          <p style={{ marginBottom: '1rem' }}>
            <strong>Stock:</strong> {product.stock > 0 ? `${product.stock} available` : 'Out of stock'}
          </p>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
            <div className="form-group" style={{ marginBottom: 0, flex: '0 0 100px' }}>
              <label>Quantity</label>
              <input
                type="number"
                min="1"
                max={product.stock}
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              />
            </div>
            <button
              className="button button-success"
              onClick={handleAddToCart}
              disabled={product.stock === 0}
              style={{ alignSelf: 'flex-end' }}
            >
              Add to Cart
            </button>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'white', padding: '2rem', borderRadius: '8px', marginTop: '2rem' }}>
        <h2>Reviews ({reviews.length})</h2>
        {reviews.length === 0 ? (
          <p style={{ color: '#666' }}>No reviews yet</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {reviews.map(review => (
              <div key={review.id} style={{ borderBottom: '1px solid #eee', paddingBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <strong>Rating: {review.rating}/5</strong>
                  <small style={{ color: '#999' }}>
                    {new Date(review.created_at).toLocaleDateString()}
                  </small>
                </div>
                <p>{review.comment}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProductDetail;
