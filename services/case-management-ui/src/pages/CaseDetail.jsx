import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API } from '../App'

function DetailRow({ label, children, isLast }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'row',
      padding: '1rem',
      borderBottom: isLast ? 'none' : '1px solid var(--border-color)',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      <div style={{ width: '250px', color: 'var(--text-muted)', fontSize: '0.9375rem', fontWeight: 500 }}>
        {label}:
      </div>
      <div style={{ flex: 1, fontSize: '0.9375rem', color: 'var(--text-main)', wordBreak: 'break-all' }}>
        {children}
      </div>
    </div>
  )
}

export default function CaseDetail() {
  const { id }  = useParams()
  const navigate = useNavigate()
  const [cas, setCas]       = useState(null)
  const [analystId, setAid] = useState('analyst-01')
  const [decision, setDec]  = useState('CONFIRMED_FRAUD')
  const [notes, setNotes]   = useState('')
  const [submitted, setSub] = useState(false)
  const [loading, setLoad]  = useState(true)

  useEffect(() => {
    fetch(`${API}/cases/${id}`)
      .then(r => r.json())
      .then(d => { setCas(d); setLoad(false) })
      .catch(() => setLoad(false))
  }, [id])

  const submitReview = () =>
    fetch(`${API}/cases/${id}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analyst_id: analystId, analyst_decision: decision, notes }),
    }).then(() => {
      setSub(true)
      setCas(prev => ({ ...prev, decision }))
    })

  if (loading) return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Loading...</div>
  if (!cas)    return <div style={{ padding: '2rem', color: 'var(--text-muted)' }}>Case not found.</div>

  const getMethodBadge = (dec) => {
    switch (dec) {
      case 'APPROVE': return <span className="badge badge-success">Approve</span>
      case 'REVIEW': return <span className="badge badge-warning">Review</span>
      case 'BLOCK':
      case 'CONFIRMED_FRAUD': return <span className="badge badge-danger">Block</span>
      default: return <span className="badge badge-secondary">{dec}</span>
    }
  }

  const inputStyle = {
    width: '100%', padding: '0.5rem 0.75rem', borderRadius: '0.375rem', outline: 'none',
    border: '1px solid var(--border-color)', fontSize: '0.9375rem', color: 'var(--text-main)',
    background: 'var(--bg-card)',
    fontFamily: 'Inter, sans-serif', boxSizing: 'border-box',
    transition: 'border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out',
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <button 
          onClick={() => navigate(-1)} 
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: 0, color: 'var(--text-muted)' }}
          title="Go Back"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
        </button>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
          Transaction Details
        </h2>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', background: 'var(--th-bg)', borderTopLeftRadius: '0.5rem', borderTopRightRadius: '0.5rem' }}>
          <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-main)' }}>Overview</div>
        </div>
        
        <div>
          <DetailRow label="Transaction Hash">
            <span style={{ fontFamily: 'monospace' }}>{cas.transaction_id}</span>
          </DetailRow>
          <DetailRow label="Status">
            {getMethodBadge(cas.decision)}
          </DetailRow>
          <DetailRow label="Time">
            {cas.created_at ? new Date(cas.created_at).toLocaleString() : '—'}
          </DetailRow>
          <DetailRow label="From">
            <span style={{ color: 'var(--link-color)' }}>{cas.user_id}</span>
          </DetailRow>
          <DetailRow label="To">
            {cas.merchant_name} {cas.merchant_category ? `(${cas.merchant_category})` : ''}
          </DetailRow>
          <DetailRow label="Value">
            ${Number(cas.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </DetailRow>
          <DetailRow label="Payment Method">
            <span className="badge badge-secondary" style={{ background: 'var(--border-color)', color: 'var(--text-main)' }}>
              {cas.payment_method || 'N/A'}
            </span>
          </DetailRow>
          <DetailRow label="Channel">
            {cas.channel}
          </DetailRow>
          <DetailRow label="Locations">
            User: {cas.user_country} | Merchant: {cas.merchant_country}
          </DetailRow>
          <DetailRow label="Fraud Score">
            {Number(cas.final_score || 0).toFixed(4)}
          </DetailRow>
          <DetailRow label="Triggered Rules" isLast>
            {(cas.triggered_rules || []).length === 0
              ? <span style={{ color: 'var(--text-muted)' }}>None</span>
              : (cas.triggered_rules || []).map(r => (
                <span key={r} className="badge" style={{
                  background: '#f8d7da', color: '#721c24', marginRight: 6, marginBottom: 6, border: '1px solid #f5c6cb'
                }}>
                  {r.replace(/_/g, ' ')}
                </span>
              ))
            }
          </DetailRow>
        </div>
      </div>

      <div className="card">
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', background: 'var(--th-bg)', borderTopLeftRadius: '0.5rem', borderTopRightRadius: '0.5rem' }}>
          <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-main)' }}>Analyst Review</div>
        </div>
        
        <div style={{ padding: '1.5rem' }}>
          {submitted ? (
            <div style={{ background: '#d4edda', color: '#155724', padding: '1rem', borderRadius: '0.25rem', border: '1px solid #c3e6cb' }}>
              Review submitted successfully. Decision updated to <strong>{decision}</strong>.
            </div>
          ) : (
            <div style={{ maxWidth: '500px' }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem', color: 'var(--text-main)' }}>
                  Analyst ID
                </label>
                <input value={analystId} onChange={e => setAid(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem', color: 'var(--text-main)' }}>
                  Decision
                </label>
                <select value={decision} onChange={e => setDec(e.target.value)} style={inputStyle}>
                  <option value="CONFIRMED_FRAUD">Confirmed fraud</option>
                  <option value="FALSE_POSITIVE">False positive</option>
                  <option value="NEEDS_INFO">Needs more info</option>
                </select>
              </div>
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.875rem', color: 'var(--text-main)' }}>
                  Notes
                </label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
              </div>
              <button onClick={submitReview} style={{
                padding: '0.5rem 1rem', borderRadius: '0.375rem',
                background: 'var(--link-color)', color: '#fff', border: '1px solid var(--link-color)',
                fontSize: '0.875rem', fontWeight: 500, cursor: 'pointer',
              }}>
                Submit Review
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}