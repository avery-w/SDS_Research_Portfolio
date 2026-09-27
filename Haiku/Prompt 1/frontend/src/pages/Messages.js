import React, { useState, useEffect } from 'react';
import { messagesAPI } from '../services/api';
import '../App.css';

function Messages() {
  const [messages, setMessages] = useState([]);
  const [recipientId, setRecipientId] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMessages();
  }, []);

  const fetchMessages = async () => {
    try {
      const response = await messagesAPI.list();
      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!recipientId || !content) return;

    try {
      await messagesAPI.send({
        recipient_id: parseInt(recipientId),
        content
      });
      setContent('');
      fetchMessages();
    } catch (error) {
      alert('Error sending message');
    }
  };

  if (loading) return <div className="loading">Loading messages...</div>;

  return (
    <div className="container">
      <h1 className="page-title">Messages</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', height: 'fit-content' }}>
          <h3>Send Message</h3>
          <form onSubmit={handleSend}>
            <div className="form-group">
              <label>Recipient ID</label>
              <input
                type="number"
                value={recipientId}
                onChange={(e) => setRecipientId(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Message</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows="4"
                required
              />
            </div>
            <button type="submit" className="button">Send</button>
          </form>
        </div>

        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px' }}>
          <h3>Message Thread</h3>
          {messages.length === 0 ? (
            <p style={{ color: '#666' }}>No messages</p>
          ) : (
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {messages.map(msg => (
                <div
                  key={msg.id}
                  style={{
                    marginBottom: '1rem',
                    padding: '0.75rem',
                    backgroundColor: msg.sender_id === parseInt(localStorage.getItem('userId') || '0') ? '#e3f2fd' : '#f5f5f5',
                    borderRadius: '4px'
                  }}
                >
                  <small style={{ color: '#999' }}>
                    {msg.sender_id === parseInt(localStorage.getItem('userId') || '0') ? 'You' : `User ${msg.sender_id}`}
                  </small>
                  <p style={{ marginTop: '0.25rem' }}>{msg.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Messages;
