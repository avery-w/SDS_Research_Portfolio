import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Header.css';

function Header({ isAuthenticated, userRole }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    navigate('/');
    window.location.reload();
  };

  return (
    <header className="header">
      <div className="container">
        <div className="header-logo">
          <Link to="/">Marketplace</Link>
        </div>
        <nav className="header-nav">
          <Link to="/">Browse</Link>
          {isAuthenticated && <Link to="/cart">Cart</Link>}
          {isAuthenticated && <Link to="/orders">Orders</Link>}
          {isAuthenticated && <Link to="/messages">Messages</Link>}
          {isAuthenticated && userRole === 'seller' && <Link to="/seller">Store</Link>}
          {isAuthenticated && userRole === 'admin' && <Link to="/admin">Admin</Link>}
          {isAuthenticated && <Link to="/profile">Profile</Link>}
        </nav>
        <div className="header-auth">
          {isAuthenticated ? (
            <button onClick={handleLogout}>Logout</button>
          ) : (
            <>
              <Link to="/login">Login</Link>
              <Link to="/register">Register</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
