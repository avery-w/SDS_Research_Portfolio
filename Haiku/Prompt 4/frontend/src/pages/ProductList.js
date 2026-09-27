import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ProductList() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, [search]);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/products`, {
        params: { search, limit: 50 }
      });
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="container"><p>Loading products...</p></div>;
  }

  return (
    <div className="container">
      <h1>Browse Products</h1>
      <input
        type="text"
        placeholder="Search products..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ maxWidth: '400px', marginTop: '1rem' }}
      />

      <div className="grid">
        {products.map((product) => (
          <Link
            key={product.id}
            to={`/product/${product.id}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="card">
              <div className="card-title">{product.name}</div>
              <p style={{ color: '#666', fontSize: '0.9rem', margin: '0.5rem 0' }}>
                {product.description.substring(0, 100)}...
              </p>
              <div className="card-price">${product.price.toFixed(2)}</div>
              <p style={{ fontSize: '0.85rem', color: '#999' }}>
                {product.quantity_available > 0 ? (
                  <span style={{ color: '#28a745' }}>In Stock ({product.quantity_available})</span>
                ) : (
                  <span style={{ color: '#dc3545' }}>Out of Stock</span>
                )}
              </p>
            </div>
          </Link>
        ))}
      </div>

      {products.length === 0 && (
        <p style={{ textAlign: 'center', marginTop: '2rem', color: '#666' }}>
          No products found. Try a different search.
        </p>
      )}
    </div>
  );
}
