import React from 'react';
import { Link } from 'react-router-dom';
import '../App.css';

function Home() {
  return (
    <div className="container">
      <div className="page-title">Welcome to ECommerce Marketplace</div>

      <div style={{ textAlign: 'center', padding: '2rem', backgroundColor: 'white', borderRadius: '8px', marginBottom: '2rem' }}>
        <h2>Your Premier Online Shopping Destination</h2>
        <p style={{ margin: '1rem 0', fontSize: '1.1rem', color: '#666' }}>
          Discover millions of products from trusted sellers around the world
        </p>
        <Link to="/products" className="button" style={{ display: 'inline-block', marginTop: '1rem' }}>
          Start Shopping
        </Link>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
        <div className="card">
          <div className="card-content">
            <h3>Browse Products</h3>
            <p>Explore thousands of products across multiple categories</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <h3>Secure Checkout</h3>
            <p>Fast and secure payment processing with multiple options</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <h3>Seller Network</h3>
            <p>Shop from trusted sellers and message them directly</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <h3>Easy Returns</h3>
            <p>Hassle-free returns and refunds within 30 days</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <h3>Order Tracking</h3>
            <p>Track your orders in real-time with delivery updates</p>
          </div>
        </div>
        <div className="card">
          <div className="card-content">
            <h3>AI Assistant</h3>
            <p>Get instant help from our AI chatbot 24/7</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
