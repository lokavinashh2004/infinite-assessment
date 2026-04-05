import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './index.css';
import './App.css';
import Chatbot from './Chatbot';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Backend returns snake_case keys in checks_passed
const CHECKS = [
  { key: 'policy_exists',       label: 'Policy Exists' },
  { key: 'policy_active',       label: 'Policy Active' },
  { key: 'date_in_range',       label: 'Date In Range' },
  { key: 'waiting_period_met',  label: 'Waiting Period Met' },
  { key: 'treatments_covered',  label: 'Treatments Covered' },
  { key: 'amount_within_limit', label: 'Amount Within Limit' },
];

const dc = (d = '') => {
  if (d.toLowerCase().includes('reject')) return 'rejected';
  if (d.toLowerCase().includes('partial')) return 'partial';
  return 'approved';
};

export default function App() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [pipelineStep, setPipelineStep] = useState(-1);
  const [toasts, setToasts] = useState([]);
  const [health, setHealth] = useState('checking');
  const [openRules, setOpenRules] = useState(false);
  const [openLogs, setOpenLogs] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    axios.get(`${API}/health`)
      .then(r => setHealth(r.data.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setHealth('offline'));
  }, []);

  const toast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(p => [...p, { id, message, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4000);
  };

  const setFileSafe = (f) => {
    if (!f) return;
    const ok = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff'];
    if (!ok.includes(f.type) && !f.name.endsWith('.tiff'))
      return toast('Unsupported file. Use PDF, PNG, JPG or TIFF.', 'error');
    if (f.size > 20 * 1024 * 1024)
      return toast('File must be under 20 MB.', 'error');
    setFile(f);
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!file || isProcessing) return;
    setIsProcessing(true);
    setResult(null);
    setPipelineStep(0);

    const timer = setInterval(() => {
      setPipelineStep(p => {
        if (p < 4) return p + 1;
        clearInterval(timer);
        return p;
      });
    }, 900);

    const fd = new FormData();
    fd.append('file', file);

    try {
      const { data } = await axios.post(`${API}/claims/process`, fd);
      clearInterval(timer);
      setPipelineStep(5);
      setResult(data);
      document.title = `${dc(data.decision) === 'approved' ? '✓' : '✗'} ${data.decision} — ClaimCopilot`;
      toast('Claim processed successfully.', 'success');
    } catch (err) {
      clearInterval(timer);
      setPipelineStep(-1);
      toast(err.response?.data?.detail || 'Processing failed. Is the backend running?', 'error');
    } finally {
      setTimeout(() => setIsProcessing(false), 400);
    }
  };

  const decisionKey = result ? dc(result.decision) : '';

  // ── SCREEN 1: Upload (centered) ──────────────────────────────
  if (!result) {
    return (
      <div className="upload-screen">
        <div className="upload-brand" style={{ marginBottom: 24, alignSelf: 'center' }}>MCP<span>Assistant</span></div>

        <div className="upload-layout">
          {/* ── Left: Upload card ── */}
          <div className="upload-card">
            <div className="upload-card-header">
              <div className="upload-card-title">Upload Claim Document</div>
              <div className="api-badge">
                <div className={`api-dot ${health}`} />
                {health === 'online' ? 'API Online' : health === 'offline' ? 'Offline' : 'Checking…'}
              </div>
            </div>

            <div className="upload-card-body">
              {/* Drop zone */}
              <div
                className={`drop-zone${isDragging ? ' dragging' : ''}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={e => { e.preventDefault(); setIsDragging(false); setFileSafe(e.dataTransfer.files[0]); }}
              >
                <input
                  ref={fileRef}
                  type="file"
                  hidden
                  accept=".pdf,.png,.jpg,.jpeg,.tiff"
                  onChange={e => setFileSafe(e.target.files[0])}
                />
                {file ? (
                  <div className="dz-file-selected">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--accent)' }}>
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M13 2v7h7" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <div className="dz-filename">{file.name}</div>
                    <button className="dz-clear" onClick={e => { e.stopPropagation(); setFile(null); }}>
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M18 6L6 18M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="dz-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    </div>
                    <div className="dz-title">Drop file here or click to browse</div>
                    <div className="dz-hint">PDF · PNG · JPG · TIFF &nbsp;—&nbsp; max 20 MB</div>
                  </>
                )}
              </div>

              {/* Pipeline (shows when processing) */}
              {(isProcessing || pipelineStep >= 0) && (
                <div className="pipeline">
                  <div className="pipeline-track">
                    {['File Read', 'AI Extract', 'RAG Search', 'Policy Lookup', 'Validate'].map((s, i) => {
                      const state = pipelineStep > i ? 'done' : pipelineStep === i ? 'active' : 'waiting';
                      return (
                        <React.Fragment key={s}>
                          <div className="pip-step">
                            <div className={`pip-dot ${state}`}>
                              {state === 'done' && (
                                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              )}
                            </div>
                            <div className={`pip-lbl ${state}`}>{s}</div>
                          </div>
                          {i < 4 && (
                            <div className="pip-line">
                              <div className={`fill${pipelineStep > i ? ' done' : ''}`} />
                            </div>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Submit */}
              <button className="btn-go" disabled={!file || isProcessing} onClick={handleSubmit}>
                {isProcessing
                  ? <><div className="spinner" /> Analysing…</>
                  : 'Process Claim'}
              </button>
            </div>
          </div>

          {/* ── Right: How it works panel ── */}
          <div className="how-panel">
            <div className="how-panel-header">How It Works</div>
            <div className="how-steps">
              <div className="how-step">
                <div className="how-step-num">1</div>
                <div className="how-step-body">
                  <div className="how-step-title">File Reading</div>
                  <div className="how-step-desc">OCR and routing via multimodal LLMs depending on document.</div>
                  
                </div>
              </div>
              <div className="how-step">
                <div className="how-step-num">2</div>
                <div className="how-step-body">
                  <div className="how-step-title">Extraction</div>
                  <div className="how-step-desc">Structured data formatting of required fields from the context.</div>
                  
                </div>
              </div>
              <div className="how-step">
                <div className="how-step-num">3</div>
                <div className="how-step-body">
                  <div className="how-step-title">RAG Search</div>
                  <div className="how-step-desc">Retrieving specific coverage clauses relevant to the claim.</div>
                  
                </div>
              </div>
              <div className="how-step">
                <div className="how-step-num">4</div>
                <div className="how-step-body">
                  <div className="how-step-title">Validation</div>
                  <div className="how-step-desc">Running deterministic execution logic validating claim policy rules.</div>
                  <div className="how-tag">python</div>
                </div>
              </div>
              <div className="how-step" style={{ paddingBottom: 16 }}>
                <div className="how-step-num">5</div>
                <div className="how-step-body">
                  <div className="how-step-title">Decisioning</div>
                  <div className="how-step-desc">Synthesising all inputs and returning the final approval status.</div>
                  <div className="how-tag">agentic</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Toasts */}
        <div className="toasts">
          {toasts.map(t => (
            <div key={t.id} className={`toast ${t.type}`}>
              <span className="toast-msg">{t.message}</span>
              <button className="toast-x" onClick={() => setToasts(p => p.filter(x => x.id !== t.id))}>×</button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── SCREEN 2: Results + Chat ─────────────────────────────────
  return (
    <div className="results-screen">
      {/* Topbar */}
      <header className="results-topbar">
        <div className="topbar-brand">MCP<span>Assistant</span></div>
        <div className="topbar-right">
          <button className="btn-new" onClick={() => { setResult(null); setFile(null); setPipelineStep(-1); }}>
            ← New Claim
          </button>
        </div>
      </header>

      {/* Decision bar */}
      <div className={`decision-bar`} style={{ borderLeft: `3px solid var(--${decisionKey === 'approved' ? 'green' : decisionKey === 'rejected' ? 'red' : 'amber'})` }}>
        <div className="db-left">
          <div className={`db-verdict ${decisionKey}`}>
            {decisionKey === 'approved' ? '✓' : decisionKey === 'rejected' ? '✗' : '~'} {result.decision}
          </div>
          <div className="db-reason">{result.reason}</div>
        </div>
        <div className="db-amount">
          <div className="db-amount-lbl">Amount Approved</div>
          <div className={`db-amount-val ${decisionKey}`}>
            <CountUp value={result.approved_amount} />
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="metrics-bar">
        {[
          { label: 'Patient', value: result.patient_name },
          { label: 'Policy ID', value: result.policy_id, mono: true },
          { label: 'Total Claimed', value: `₹${result.total_claimed.toLocaleString('en-IN')}` },
          { label: 'Processed', value: new Date(result.timestamp).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) },
        ].map(m => (
          <div key={m.label} className="metric-cell">
            <div className="metric-lbl">{m.label}</div>
            <div className={`metric-val${m.mono ? ' mono' : ''}`}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Body: checks panel + chat */}
      <div className="results-body">
        {/* Left: verification checks + logs */}
        <aside className="checks-panel">
          <div className="checks-section-title">Verification Checks</div>
          {CHECKS.map((c, i) => {
            const ok = result.checks_passed.includes(c.key);
            return (
              <div key={c.key} className="check-row animate" style={{ animationDelay: `${i * 60}ms` }}>
                <div className={`chk-icon ${ok ? 'pass' : 'fail'}`}>{ok ? '✓' : '✗'}</div>
                <div className="chk-name">{c.label}</div>
                <div className={`chk-tag ${ok ? 'pass' : 'fail'}`}>{ok ? 'PASS' : 'FAIL'}</div>
              </div>
            );
          })}

          {/* Clauses */}
          {result.clauses_cited?.length > 0 && (
            <div className="clauses-section">
              <div className="clauses-section-title">Clauses Cited</div>
              <div className="clauses-row">
                {result.clauses_cited.map(c => <span key={c} className="clause">#{c}</span>)}
              </div>
            </div>
          )}

          {/* RAG Rules collapsible */}
          <button className="coll-header" onClick={() => setOpenRules(v => !v)}>
            Policy Rules
            <svg className={`coll-chevron${openRules ? ' open' : ''}`} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          <div className={`coll-body${openRules ? ' open' : ''}`}>
            <div className="rules-list">
              {result.rag_rules_used.map((r, i) => <div key={i} className="rule-item">{r}</div>)}
            </div>
          </div>

          {/* Execution log collapsible */}
          <button className="coll-header" onClick={() => setOpenLogs(v => !v)}>
            Execution Log
            <svg className={`coll-chevron${openLogs ? ' open' : ''}`} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          <div className={`coll-body${openLogs ? ' open' : ''}`}>
            <div className="log-list">
              {result.execution_log.map((l, i) => <div key={i} className="log-entry">{l}</div>)}
            </div>
          </div>
        </aside>

        {/* Right: chat */}
        <div className="chat-col">
          <Chatbot claimContext={result} />
        </div>
      </div>

      {/* Toasts */}
      <div className="toasts">
        {toasts.map(t => (
          <div key={t.id} className={`toast ${t.type}`}>
            <span className="toast-msg">{t.message}</span>
            <button className="toast-x" onClick={() => setToasts(p => p.filter(x => x.id !== t.id))}>×</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function CountUp({ value }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const end = Number(value) || 0;
    let cur = 0;
    const step = end / 60;
    const id = setInterval(() => {
      cur = Math.min(cur + step, end);
      setN(Math.floor(cur));
      if (cur >= end) clearInterval(id);
    }, 16);
    return () => clearInterval(id);
  }, [value]);
  return <>{n.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}</>;
}
