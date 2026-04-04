import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './Chatbot.css';

export default function Chatbot({ claimContext }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! I'm your MCP Bot. Ask me anything about your claim or policy rules!" }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (claimContext && claimContext.decision) {
      const decisionStr = claimContext.decision.toLowerCase();
      const amountStr = claimContext.approved_amount ? ` ₹${claimContext.approved_amount.toLocaleString()}` : '';
      const autoMessage = `Your claim was **${decisionStr}**${amountStr}. \nReason: ${claimContext.reason}\n\nWould you like me to explain any part of this policy or adjudication decision?`;
      
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: autoMessage }
      ]);
    }
  }, [claimContext]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const newMessages = [...messages, { role: 'user', content: inputMessage }];
    setMessages(newMessages);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Send history avoiding the initial greeting message
      const history = newMessages.slice(1).map(m => ({ role: m.role, content: m.content }));
      
      const response = await axios.post('http://localhost:8000/chat', {
        message: inputMessage,
        context: claimContext, 
        history: history.slice(0, -1) 
      });
      
      setMessages([...newMessages, { role: 'assistant', content: response.data.reply }]);
    } catch (err) {
      setMessages([...newMessages, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the policy backend." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderText = (text) => {
    // Basic rendering to support new lines and bolding text that has **
    return text.split('\n').map((line, i) => {
      // Replace **text** with <strong>text</strong>
      const lineHtml = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return (
        <span key={i}>
          <span dangerouslySetInnerHTML={{ __html: lineHtml }} />
          <br />
        </span>
      );
    });
  };

  return (
    <div className="chatbot-card fade-in">
      <div className="chat-window">
        <div className="chat-header">
          <h3>MCP</h3>
        </div>
        
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-bubble">
                {renderText(msg.content)}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <div className="message-bubble loading">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot :dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <form className="chat-input-form" onSubmit={handleSendMessage}>
          <input 
            type="text" 
            placeholder="Ask about your policy or claim..." 
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={isLoading}
          />
          <button type="submit" disabled={!inputMessage.trim() || isLoading}>Send</button>
        </form>
      </div>
    </div>
  );
}
