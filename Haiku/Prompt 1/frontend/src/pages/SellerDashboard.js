import React, { useState, useEffect } from 'react';
import { sellerAPI } from '../services/api';
import '../App.css';

function SellerDashboard() {
  const [activeTab, setActiveTab] = useState('products');
  const [store, setStore] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [newProduct, setNewProduct] = useState({
    name: '',
    description: '',
    price: '',
    stock: '',
    sku: '',
    category: '',
    image_urls: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const storeRes = await sellerAPI.getStore();
      setStore(storeRes.data);

      const productsRes = await sellerAPI.listProducts();
      setProducts(productsRes.data);

      const ordersRes = await sellerAPI.getOrders();
      setOrders(ordersRes.data);

      const analyticsRes = await sellerAPI.getAnalytics();
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    try {
      await sellerAPI.createProduct({
        ...newProduct,
        price: parseFloat(newProduct.price),
        stock: parseInt(newProduct.stock)
      });
      setNewProduct({ name: '', description: '', price: '', stock: '', sku: '', category: '', image_urls: '' });
      fetchData();
    } catch (error) {
      alert('Error adding product: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Seller Dashboard</h1>

      {store && (
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem' }}>
          <h2>{store.name}</h2>
          <p style={{ color: '#666', marginTop: '0.5rem' }}>{store.description}</p>
        </div>
      )}

      {analytics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ backgroundColor: '#e3f2fd', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Sales</h4>
            <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#2196F3' }}>
              ${analytics.total_sales}
            </p>
          </div>
          <div style={{ backgroundColor: '#e8f5e9', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Total Orders</h4>
            <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#4CAF50' }}>
              {analytics.total_orders}
            </p>
          </div>
          <div style={{ backgroundColor: '#fff3e0', padding: '1.5rem', borderRadius: '8px' }}>
            <h4>Products</h4>
            <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ff9800' }}>
              {analytics.active_products}/{analytics.total_products}
            </p>
          </div>
        </div>
      )}

      <div style={{ marginTop: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', borderBottom: '2px solid #ddd' }}>
          <button
            className={activeTab === 'products' ? 'button' : ''}
            onClick={() => setActiveTab('products')}
            style={{ backgroundColor: activeTab === 'products' ? '#2196F3' : 'transparent', color: activeTab === 'products' ? 'white' : '#666' }}
          >
            Products
          </button>
          <button
            className={activeTab === 'orders' ? 'button' : ''}
            onClick={() => setActiveTab('orders')}
            style={{ backgroundColor: activeTab === 'orders' ? '#2196F3' : 'transparent', color: activeTab === 'orders' ? 'white' : '#666' }}
          >
            Orders
          </button>
        </div>

        {activeTab === 'products' && (
          <>
            <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem' }}>
              <h3>Add New Product</h3>
              <form onSubmit={handleAddProduct}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                  <div className="form-group">
                    <input
                      placeholder="Name"
                      value={newProduct.name}
                      onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <input
                      placeholder="SKU"
                      value={newProduct.sku}
                      onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <input
                      type="number"
                      placeholder="Price"
                      value={newProduct.price}
                      onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <input
                      type="number"
                      placeholder="Stock"
                      value={newProduct.stock}
                      onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                    <textarea
                      placeholder="Description"
                      value={newProduct.description}
                      onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
                      required
                    />
                  </div>
                </div>
                <button type="submit" className="button">Add Product</button>
              </form>
            </div>

            <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
              <h3>Your Products</h3>
              {products.length === 0 ? (
                <p style={{ color: '#666' }}>No products yet</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Price</th>
                      <th>Stock</th>
                      <th>Category</th>
                    </tr>
                  </thead>
                  <tbody>
                    {products.map(product => (
                      <tr key={product.id}>
                        <td>{product.name}</td>
                        <td>${product.price}</td>
                        <td>{product.stock}</td>
                        <td>{product.category}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}

        {activeTab === 'orders' && (
          <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
            <h3>Orders</h3>
            {orders.length === 0 ? (
              <p style={{ color: '#666' }}>No orders yet</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Status</th>
                    <th>Total</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(order => (
                    <tr key={order.id}>
                      <td>#{order.id}</td>
                      <td><span className="role">{order.status}</span></td>
                      <td>${order.total_amount}</td>
                      <td>{new Date(order.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SellerDashboard;
