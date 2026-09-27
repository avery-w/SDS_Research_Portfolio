import { Outlet, Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../context/authStore";
import { ShoppingCart, User, LogOut, Store, Shield, MessageCircle } from "lucide-react";

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <Link to="/" className="text-xl font-bold text-indigo-600">
                Marketplace
              </Link>
              <Link to="/" className="text-gray-700 hover:text-indigo-600">Products</Link>
              <Link to="/cart" className="text-gray-700 hover:text-indigo-600">
                <ShoppingCart className="w-5 h-5" />
              </Link>
              <Link to="/orders" className="text-gray-700 hover:text-indigo-600">Orders</Link>
              {user?.role === "seller" && (
                <Link to="/seller" className="text-gray-700 hover:text-indigo-600">
                  <Store className="w-5 h-5" />
                </Link>
              )}
              {user?.role === "admin" && (
                <Link to="/admin" className="text-gray-700 hover:text-indigo-600">
                  <Shield className="w-5 h-5" />
                </Link>
              )}
              <Link to="/chat/1" className="text-gray-700 hover:text-indigo-600">
                <MessageCircle className="w-5 h-5" />
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">{user?.full_name}</span>
              <button onClick={handleLogout} className="text-gray-500 hover:text-red-600">
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
