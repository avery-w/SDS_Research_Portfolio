import React, { useState, useEffect } from 'react';
import { messages } from '../api';
import '../styles/Common.css';

function Messages() {
  const [messageList, setMessageList] = useState([]);
  const [recipientId, setRecipientId] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');

  useEffect(() => {
    messages.list().then((res) => setMessageList(res.data)).catch(() => alert('Failed to load messages'));
  }, []);

  const handleSend = async (e) => {
    e.preventDefault();
    try {
      await messages.send(recipientId, subject, content);
      setRecipientId('');
      setSubject('');
      setContent('');
      const res = await messages.list();
      setMessageList(res.data);
    } catch (err) {
      alert('Failed to send message');
    }
  };

  return (
    <div className="container">
      <h1>Messages</h1>
      <div className="message-list">
        {messageList.map((msg) => (
          <div key={msg.id} className={`message-item ${!msg.is_read ? 'unread' : ''}`}>
            <div className="message-preview">
              <div>
                <p className="message-subject">{msg.subject}</p>
                <p className="message-sender">From: {msg.sender?.email}</p>
              </div>
              <span className="message-time">{new Date(msg.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSend} style={{ marginTop: '2rem' }}>
        <h2>Send Message</h2>
        <div className="form-group">
          <label>Recipient ID</label>
          <input type="number" value={recipientId} onChange={(e) => setRecipientId(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Subject</label>
          <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Message</label>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} required />
        </div>
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

export default Messages;
