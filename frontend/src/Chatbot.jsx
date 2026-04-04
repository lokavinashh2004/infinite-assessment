import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './Chatbot.css';

const API = import.meta.env.VITE_API_URL || 'https://infinite-assessment.onrender.com';
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function Chatbot({ claimContext }) {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: 'bot',
      text: 'Claim processed! Ask me anything about the decision, policy rules, or coverage details.',
      time: now()
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef(null);

  // Auto-push summary when claim context arrives
  useEffect(() => {
    if (!claimContext) return;
    const amt = Number(claimContext.approved_amount).toLocaleString('en-IN', {
      style: 'currency', currency: 'INR', maximumFractionDigits: 0
    });
    const clauses = claimContext.clauses_cited?.join(', ') || 'none';
    push('bot',
      `Claim for ${claimContext.patient_name} → ${claimContext.decision} (${amt}). ` +
      `Reason: ${claimContext.reason}. Clauses: ${clauses}.`
    );
  }, [claimContext]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const push = (role, text) =>
    setMessages(p => [...p, { id: Date.now() + Math.random(), role, text, time: now() }]);

  const send = async () => {
    const msg = input.trim();
    if (!msg) return;
    push('user', msg);
    setInput('');
    setIsTyping(true);
    try {
      const { data } = await axios.post(`${API}/chat`, {
        message: msg,
        context: claimContext
      });
      push('bot', data.reply);
    } catch {
      push('bot', "Sorry, I couldn't reach the server right now.");
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-wrap">
      {/* Header */}
      <div className="chat-head">
        <div className="chat-head-left">
          <div className="chat-avatar">AI</div>
          <div>
            <div className="chat-title">ClaimCopilot AI</div>
            <div className="chat-sub">Ask anything about this claim</div>
          </div>
        </div>
        <div className="chat-status">
          <div className="chat-status-dot" style={{ background: claimContext ? 'var(--green)' : 'var(--amber)' }} />
          {claimContext ? 'Ready' : 'Awaiting claim'}
        </div>
      </div>

      {/* Messages */}
      <div className="msgs">
        {messages.map(m => (
          <div key={m.id} className={`msg ${m.role}`}>
            <div className="bubble">{m.text}</div>
            <div className="msg-time">{m.time}</div>
          </div>
        ))}
        {isTyping && (
          <div className="typing-bubble">
            <div className="dot-b" /><div className="dot-b" /><div className="dot-b" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-row">
        <input
          className="chat-input"
          placeholder="Ask about the claim, policy, or coverage…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
        />
        <button className="btn-send" disabled={!input.trim()} onClick={send}>
          Send
        </button>
      </div>
    </div>
  );
}
