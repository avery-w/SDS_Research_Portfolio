import React, { useState, useRef, useEffect } from 'react';
import { chatbotAPI } from '../services/api';
import '../App.css';

function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, text: 'Hi! How can I help you today?', sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');
    setMessages([...messages, { id: Date.now(), text: userMessage, sender: 'user' }]);

    try {
      setLoading(true);
      const response = await chatbotAPI.query(userMessage);
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: response.data.response,
        sender: 'bot',
        suggestions: response.data.suggested_sellers
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {isOpen ? (
        <div className="chatbot">
          <div className="chatbot-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Customer Support</span>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '1.2rem'
                }}
              >
                ×
              </button>
            </div>
          </div>
          <div className="chatbot-messages">
            {messages.map(msg => (
              <div key={msg.id} className={msg.sender === 'user' ? 'message user-message' : 'message bot-message'}>
                {msg.text}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                    <p style={{ fontWeight: 'bold' }}>Suggested sellers:</p>
                    {msg.suggestions.map((seller, idx) => (
                      <p key={idx}>{seller}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="message bot-message">Typing...</div>}
            <div ref={messagesEndRef} />
          </div>
          <form onSubmit={handleSend} className="chatbot-input">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question..."
              disabled={loading}
            />
            <button type="submit" disabled={loading}>Send</button>
          </form>
        </div>
      ) : (
        <button
          className="button"
          onClick={() => setIsOpen(true)}
          style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            borderRadius: '50%',
            width: '60px',
            height: '60px',
            padding: '0',
            fontSize: '1.5rem',
            zIndex: 999
          }}
        >
          💬
        </button>
      )}
    </>
  );
}

export default Chatbot;
