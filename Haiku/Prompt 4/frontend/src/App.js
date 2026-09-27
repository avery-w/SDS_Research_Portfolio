import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';

import Login from './pages/Login';
import Register from './pages/Register';
import ProductList from './pages/ProductList';
import ProductDetail from './pages/ProductDetail';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import SellerDashboard from './pages/SellerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import Chat from './pages/Chat';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchCurrentUser(token);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async (token) => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
    }
    setLoading(false);
  };

  const handleLogin = (token, userData) => {
    localStorage.setItem('token', token);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return <div className="container"><p>Loading...</p></div>;
  }

  return (
    <AuthContext.Provider value={{ user, handleLogin, handleLogout }}>
      <Router>
        <header>
          <nav>
            <Link to="/" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
              Marketplace
            </Link>
            <div>
              <Link to="/">Products</Link>
              {user && <Link to="/cart">Cart</Link>}
              {user && <Link to="/orders">Orders</Link>}
              {user?.role === 'seller' && <Link to="/seller">Seller Dashboard</Link>}
              {user?.role === 'admin' && <Link to="/admin">Admin Dashboard</Link>}
              {user && <Link to="/chat">Chat</Link>}
              {!user ? (
                <>
                  <Link to="/login">Login</Link>
                  <Link to="/register">Register</Link>
                </>
              ) : (
                <button
                  onClick={handleLogout}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#0066cc',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                    margin: '0 1rem'
                  }}
                >
                  Logout
                </button>
              )}
            </div>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<ProductList />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          {user && <Route path="/cart" element={<Cart />} />}
          {user && <Route path="/checkout" element={<Checkout />} />}
          {user && <Route path="/orders" element={<Orders />} />}
          {user?.role === 'seller' && <Route path="/seller" element={<SellerDashboard />} />}
          {user?.role === 'admin' && <Route path="/admin" element={<AdminDashboard />} />}
          {user && <Route path="/chat" element={<Chat />} />}
        </Routes>
      </Router>
    </AuthContext.Provider>
  );
}

export default App;
