import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { products } from '../api';
import '../styles/Home.css';

function Home() {
  const [productList, setProductList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await products.list();
      setProductList(response.data.results || response.data);
    } catch (err) {
      setError('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    try {
      const response = await products.search(searchQuery);
      setProductList(response.data.results || response.data);
    } catch (err) {
      setError('Search failed');
    }
  };

  if (loading) return <div className="container">Loading...</div>;
  if (error) return <div className="container error">{error}</div>;

  return (
    <div className="home">
      <div className="container">
        <div className="search-section">
          <form onSubmit={handleSearch}>
            <input
              type="text"
              placeholder="Search products..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit">Search</button>
          </form>
        </div>

        <div className="products-grid">
          {productList.map((product) => (
            <Link key={product.id} to={`/products/${product.id}`} className="product-card">
              <div className="product-image">
                {product.images?.length > 0 ? (
                  <img src={product.images[0].image} alt={product.name} />
                ) : (
                  <div className="placeholder">No image</div>
                )}
              </div>
              <div className="product-info">
                <h3>{product.name}</h3>
                <p className="price">${product.price}</p>
                <p className="store">{product.store?.name}</p>
                <div className="rating">★ {product.rating}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Home;
