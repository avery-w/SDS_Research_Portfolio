import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import Home from './pages/Home';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Orders from './pages/Orders';
import Login from './pages/Login';
import Register from './pages/Register';
import SellerDashboard from './pages/SellerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import Messages from './pages/Messages';
import Chatbot from './components/Chatbot';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('userRole');
    const name = localStorage.getItem('userName');
    if (token) {
      setIsLoggedIn(true);
      setUserRole(role);
      setUserName(name);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('userName');
    setIsLoggedIn(false);
    setUserRole(null);
    window.location.href = '/';
  };

  return (
    <Router>
      <nav className="navbar">
        <Link to="/" className="logo">ECommerce</Link>
        <ul className="nav-links">
          <li><Link to="/products">Products</Link></li>
          {isLoggedIn ? (
            <>
              {userRole === 'customer' && (
                <>
                  <li><Link to="/cart">Cart</Link></li>
                  <li><Link to="/orders">Orders</Link></li>
                  <li><Link to="/messages">Messages</Link></li>
                </>
              )}
              {userRole === 'seller' && (
                <li><Link to="/seller">Store</Link></li>
              )}
              {userRole === 'admin' && (
                <li><Link to="/admin">Admin</Link></li>
              )}
              <li className="user-info">
                {userName} (<span className="role">{userRole}</span>)
              </li>
              <li><button onClick={handleLogout} className="logout-btn">Logout</button></li>
            </>
          ) : (
            <>
              <li><Link to="/login">Login</Link></li>
              <li><Link to="/register">Register</Link></li>
            </>
          )}
        </ul>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:id" element={<ProductDetail />} />
        <Route path="/login" element={<Login setIsLoggedIn={setIsLoggedIn} setUserRole={setUserRole} setUserName={setUserName} />} />
        <Route path="/register" element={<Register />} />
        {isLoggedIn && userRole === 'customer' && (
          <>
            <Route path="/cart" element={<Cart />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/messages" element={<Messages />} />
          </>
        )}
        {isLoggedIn && userRole === 'seller' && (
          <Route path="/seller" element={<SellerDashboard />} />
        )}
        {isLoggedIn && userRole === 'admin' && (
          <Route path="/admin" element={<AdminDashboard />} />
        )}
      </Routes>

      {isLoggedIn && userRole === 'customer' && <Chatbot />}
    </Router>
  );
}

export default App;
