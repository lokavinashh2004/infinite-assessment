import { useState } from 'react'
import axios from 'axios'
import './App.css'
import Chatbot from './Chatbot' // <--- Added import

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
      setResult(null)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file to upload.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await axios.post('http://localhost:8000/claims/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      setResult(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'An error occurred during processing.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>MCP</h1>
        <p>AI-Powered Medical Insurance Claim Processor</p>
      </header>

      <main className="app-main">
        <div className="upload-card">
          <h2>Upload Claim Document</h2>
          <p className="subtitle">Supported formats: PDF, PNG, JPG, TIFF</p>
          
          <form onSubmit={handleSubmit} className="upload-form">
            <div className={`file-drop-area ${file ? 'has-file' : ''}`}>
              <input 
                type="file" 
                id="file-input" 
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif" 
                onChange={handleFileChange}
              />
              <label htmlFor="file-input">
                {file ? (
                  <span className="file-name">📄 {file.name}</span>
                ) : (
                  <span className="upload-prompt">
                    <span className="upload-icon">📁</span>
                    <br/>Click to Browse or Drag File Here
                  </span>
                )}
              </label>
            </div>
            
            <button 
              type="submit" 
              className="submit-btn" 
              disabled={!file || loading}
            >
              {loading ? 'Processing...' : 'Process Claim'}
            </button>
          </form>

          {error && <div className="error-message">{error}</div>}
        </div>

        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Analyzing document and policy rules...</p>
          </div>
        )}

        {result && (
          <>
            <div className="result-card fade-in">
              <div className="result-header">
                <h2>Adjudication Decision</h2>
                <span className={`status-badge ${result.decision?.toLowerCase().replace(' ', '-')}`}>
                  {result.decision}
                </span>
              </div>
              
              <div className="result-grid">
                <div className="result-item">
                  <span className="label">Patient Name:</span>
                  <span className="value">{result.patient_name || 'N/A'}</span>
                </div>
                <div className="result-item">
                  <span className="label">Policy ID:</span>
                  <span className="value">{result.policy_id || 'N/A'}</span>
                </div>
                <div className="result-item">
                  <span className="label">Total Claimed:</span>
                  <span className="value amount">₹{result.total_claimed?.toLocaleString() || '0'}</span>
                </div>
                <div className="result-item">
                  <span className="label">Approved Amount:</span>
                  <span className="value amount highlight">₹{result.approved_amount?.toLocaleString() || '0'}</span>
                </div>
              </div>

              <div className="result-details">
                <h3>Reason</h3>
                <p>{result.reason}</p>
                
                {result.clauses_cited && result.clauses_cited.length > 0 && (
                  <>
                    <h3>Clauses Cited</h3>
                    <div className="tags">
                      {result.clauses_cited.map((clause, i) => (
                        <span key={i} className="tag">{clause}</span>
                      ))}
                    </div>
                  </>
                )}

                {result.checks_passed && result.checks_passed.length > 0 && (
                  <>
                    <h3>Verification Checks</h3>
                    <ul className="checks-list">
                      {result.checks_passed.map((check, i) => (
                        <li key={i} className="check-pass">✅ {check.replace(/_/g, ' ')}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
            <Chatbot claimContext={result} />
          </>
        )}
      </main>
    </div>
  )
}

export default App
