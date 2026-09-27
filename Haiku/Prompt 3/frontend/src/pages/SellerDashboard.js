import React, { useState, useEffect } from 'react';
import { products, orders } from '../api';
import '../styles/Common.css';

function SellerDashboard() {
  const [productList, setProductList] = useState([]);
  const [orderList, setOrderList] = useState([]);
  const [newProduct, setNewProduct] = useState({ name: '', description: '', price: '', stock: '', sku: '', category: '', weight_kg: '' });

  useEffect(() => {
    products.myProducts().then((res) => setProductList(res.data)).catch(() => {});
    orders.list().then((res) => setOrderList(res.data)).catch(() => {});
  }, []);

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      await products.create(newProduct);
      alert('Product created');
      const res = await products.myProducts();
      setProductList(res.data);
      setNewProduct({ name: '', description: '', price: '', stock: '', sku: '', category: '', weight_kg: '' });
    } catch (err) {
      alert('Failed to create product');
    }
  };

  return (
    <div className="container">
      <h1>Seller Dashboard</h1>

      <section>
        <h2>My Products</h2>
        {productList.map((prod) => (
          <div key={prod.id} className="order-card">
            <p><strong>{prod.name}</strong> - ${prod.price}</p>
            <p>Stock: {prod.stock}, SKU: {prod.sku}</p>
          </div>
        ))}
      </section>

      <section>
        <h2>Create Product</h2>
        <form onSubmit={handleCreateProduct}>
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={newProduct.description} onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })} required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Price</label>
              <input type="number" step="0.01" value={newProduct.price} onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Stock</label>
              <input type="number" value={newProduct.stock} onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>SKU</label>
              <input type="text" value={newProduct.sku} onChange={(e) => setNewProduct({ ...newProduct, sku: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Category</label>
              <input type="text" value={newProduct.category} onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })} required />
            </div>
          </div>
          <div className="form-group">
            <label>Weight (kg)</label>
            <input type="number" step="0.01" value={newProduct.weight_kg} onChange={(e) => setNewProduct({ ...newProduct, weight_kg: e.target.value })} required />
          </div>
          <button type="submit">Create Product</button>
        </form>
      </section>

      <section>
        <h2>Recent Orders</h2>
        {orderList.map((order) => (
          <div key={order.id} className="order-card">
            <p><strong>{order.order_number}</strong> - {order.status}</p>
            <p>Total: ${order.total_price}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

export default SellerDashboard;
