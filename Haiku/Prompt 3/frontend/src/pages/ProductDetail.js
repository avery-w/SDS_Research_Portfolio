import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { products, cart, chatbot } from '../api';
import '../styles/Common.css';

function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [chatMessage, setChatMessage] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProduct();
  }, [id]);

  const fetchProduct = async () => {
    try {
      const response = await products.detail(id);
      setProduct(response.data);
    } catch (err) {
      console.error('Failed to load product');
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async () => {
    try {
      await cart.addItem(id, quantity);
      alert('Added to cart');
    } catch (err) {
      alert('Failed to add to cart');
    }
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await chatbot.chat(chatMessage, id);
      setChatResponse(response.data.response);
      setChatMessage('');
    } catch (err) {
      setChatResponse('Failed to get response');
    }
  };

  if (loading) return <div className="container">Loading...</div>;
  if (!product) return <div className="container">Product not found</div>;

  return (
    <div className="container">
      <div className="product-detail">
        <div className="detail-image">
          {product.images?.length > 0 && (
            <img src={product.images[0].image} alt={product.name} />
          )}
        </div>
        <div className="detail-info">
          <h1>{product.name}</h1>
          <p className="price">${product.price}</p>
          <p className="store">By {product.store?.name}</p>
          <p className="rating">Rating: {product.rating} stars</p>
          <p className="description">{product.description}</p>
          {product.weight_kg && <p>Weight: {product.weight_kg}kg</p>}
          <p>Stock: {product.stock}</p>
          <div className="add-to-cart">
            <input type="number" min="1" max={product.stock} value={quantity} onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))} />
            <button onClick={handleAddToCart}>Add to Cart</button>
          </div>
        </div>
      </div>

      <div className="reviews-section">
        <h2>Reviews</h2>
        {product.reviews?.map((review) => (
          <div key={review.id} className="review">
            <p><strong>{review.customer?.email}</strong> - {review.rating}★</p>
            <p>{review.title}</p>
            <p>{review.content}</p>
          </div>
        ))}
      </div>

      <div className="chatbot-section">
        <h2>Ask a Question</h2>
        <form onSubmit={handleChatSubmit}>
          <input type="text" placeholder="Ask about this product..." value={chatMessage} onChange={(e) => setChatMessage(e.target.value)} required />
          <button type="submit">Send</button>
        </form>
        {chatResponse && <div className="chat-response">{chatResponse}</div>}
      </div>
    </div>
  );
}

export default ProductDetail;
