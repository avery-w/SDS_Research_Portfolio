import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchMessages();
    fetchSuggestions();
  }, []);

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API_URL}/chat/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessages(response.data);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const fetchSuggestions = async () => {
    try {
      const response = await axios.get(`${API_URL}/chat/suggestions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuggestions(response.data.suggestions);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    try {
      await axios.post(
        `${API_URL}/chat/message`,
        { content: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setInput('');
      fetchMessages();
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
  };

  return (
    <div className="container">
      <h1>Customer Support Chat</h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 250px',
        gap: '2rem',
        marginTop: '2rem'
      }}>
        <div>
          <div style={{
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '1.5rem',
            height: '400px',
            overflowY: 'auto',
            marginBottom: '1rem'
          }}>
            {messages.length === 0 ? (
              <p style={{ color: '#999' }}>Start a conversation by asking a question!</p>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    marginBottom: '1rem',
                    textAlign: msg.is_from_chatbot ? 'left' : 'right'
                  }}
                >
                  <div style={{
                    display: 'inline-block',
                    maxWidth: '80%',
                    background: msg.is_from_chatbot ? '#f0f0f0' : '#0066cc',
                    color: msg.is_from_chatbot ? '#333' : 'white',
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    wordWrap: 'break-word'
                  }}>
                    {msg.content}
                  </div>
                </div>
              ))
            )}
          </div>

          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              style={{ flex: 1 }}
            />
            <button type="submit" className="button">Send</button>
          </form>
        </div>

        <div>
          <h3>Suggested Questions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestionClick(suggestion)}
                style={{
                  background: '#f0f0f0',
                  border: '1px solid #ddd',
                  padding: '0.75rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.9rem'
                }}
                onMouseEnter={(e) => e.target.style.background = '#e0e0e0'}
                onMouseLeave={(e) => e.target.style.background = '#f0f0f0'}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
