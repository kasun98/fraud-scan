import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLiveCases, useStats } from '../App'

function StatCard({ title, value, percentage, isGreen = true, subtext = '', onClick, active }) {
  return (
    <div 
      className="card" 
      onClick={onClick}
      style={{ 
        padding: '1.25rem', 
        flex: '1 1 200px', 
        cursor: onClick ? 'pointer' : 'default',
        border: active ? '2px solid var(--link-color)' : '1px solid var(--border-color)',
        background: active ? 'var(--bg-active)' : 'var(--bg-card)'
      }}
    >
      <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>
        {title}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
        <span style={{ fontSize: '1.25rem', color: 'var(--text-main)', fontWeight: 500 }}>
          {value}
        </span>
        {percentage && (
          <span style={{ fontSize: '0.875rem', color: isGreen ? '#00a186' : '#e82646' }}>
            ({percentage})
          </span>
        )}
      </div>
      {subtext && (
        <div style={{ fontSize: '0.875rem', color: 'var(--text-light)', marginTop: '0.25rem' }}>
          {subtext}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  
  const { cases, hasMore, loading } = useLiveCases(filter, page)
  const stats = useStats()

  const getMethodBadge = (decision) => {
    switch (decision) {
      case 'APPROVE': return <span className="badge badge-success">Approve</span>
      case 'REVIEW': return <span className="badge badge-warning">Review</span>
      case 'BLOCK':
      case 'CONFIRMED_FRAUD': return <span className="badge badge-danger">Block</span>
      default: return <span className="badge badge-secondary">{decision}</span>
    }
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '0'
    return Number(num).toLocaleString('en-US')
  }

  const getAge = (dateStr) => {
    if (!dateStr) return '—'
    const seconds = Math.floor((new Date() - new Date(dateStr)) / 1000)
    if (seconds < 60) return `${seconds} secs ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes} mins ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} hrs ago`
    const days = Math.floor(hours / 24)
    return `${days} days ago`
  }

  const getRuleStyle = (rule) => {
    const colors = [
      { bg: 'rgba(232, 38, 70, 0.1)', color: '#e82646' },
      { bg: 'rgba(245, 194, 0, 0.1)', color: '#f5c200' },
      { bg: 'rgba(7, 132, 195, 0.1)', color: '#0784c3' },
      { bg: 'rgba(0, 161, 134, 0.1)', color: '#00a186' },
      { bg: 'rgba(140, 152, 164, 0.1)', color: '#8c98a4' }
    ];
    let hash = 0;
    for (let i = 0; i < rule.length; i++) {
      hash = rule.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
          Transactions
        </h2>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <StatCard 
          title="TRANSACTIONS" 
          value={formatNumber(stats?.total)} 
          onClick={() => { setFilter(''); setPage(1); }}
          active={filter === ''}
        />
        <StatCard 
          title="PENDING REVIEWS" 
          value={formatNumber(stats?.review)} 
          subtext=""
          onClick={() => { setFilter('REVIEW'); setPage(1); }}
          active={filter === 'REVIEW'}
        />
        <StatCard 
          title="BLOCKED TRANSACTIONS" 
          value={formatNumber(stats?.blocked)} 
          subtext=""
          onClick={() => { setFilter('BLOCK'); setPage(1); }}
          active={filter === 'BLOCK'}
        />
        <StatCard 
          title="FRAUD PREVENTED" 
          value={`$${formatNumber(stats?.fraud_value)}`} 
          isGreen={true}
        />
        <StatCard 
          title="APPROVED VALUE" 
          value={`$${formatNumber(stats?.safe_value)}`} 
          isGreen={true}
        />
      </div>

      <div className="card">
        <div style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)' }}>
          <div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text-main)' }}>
              {filter ? `Filtered transactions` : `More than ${formatNumber(stats?.total || cases.length)} transactions found`}
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-light)' }}>
              (Showing 50 records per page)
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <button 
              onClick={() => setPage(1)} 
              disabled={page === 1}
              style={{ padding: '0.25rem 0.5rem', border: '1px solid var(--border-color)', background: 'var(--bg-card)', borderRadius: '0.25rem', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? 'var(--text-light)' : 'var(--text-muted)' }}
            >
              First
            </button>
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))} 
              disabled={page === 1}
              style={{ padding: '0.25rem 0.5rem', border: '1px solid var(--border-color)', background: 'var(--bg-card)', borderRadius: '0.25rem', cursor: page === 1 ? 'not-allowed' : 'pointer', color: page === 1 ? 'var(--text-light)' : 'var(--text-muted)' }}
            >
              &lt;
            </button>
            <span style={{ fontSize: '0.875rem', padding: '0 0.5rem', color: 'var(--text-muted)' }}>Page {page}</span>
            <button 
              onClick={() => setPage(p => p + 1)} 
              disabled={!hasMore}
              style={{ padding: '0.25rem 0.5rem', border: '1px solid var(--border-color)', background: 'var(--bg-card)', borderRadius: '0.25rem', cursor: !hasMore ? 'not-allowed' : 'pointer', color: !hasMore ? 'var(--text-light)' : 'var(--link-color)' }}
            >
              &gt;
            </button>
          </div>
        </div>
        
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: '40px', textAlign: 'center' }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                </th>
                <th>Transaction Hash</th>
                <th>Status</th>
                <th>Age</th>
                <th>From</th>
                <th style={{ width: '40px', textAlign: 'center' }}></th>
                <th>To</th>
                <th>Amount</th>
                <th>Triggered Rules</th>
                <th>Txn Fee</th>
              </tr>
            </thead>
            <tbody>
              {cases.length === 0 && !loading && (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No transactions found
                  </td>
                </tr>
              )}
              {cases.map((c) => (
                <tr key={c.transaction_id}>
                  <td style={{ textAlign: 'center' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-light)" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  </td>
                  <td>
                    <Link to={`/cases/${c.transaction_id}`} style={{ fontFamily: 'monospace', fontWeight: 500 }}>
                      {c.transaction_id.slice(0, 14)}...
                    </Link>
                  </td>
                  <td>
                    {getMethodBadge(c.decision)}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {getAge(c.created_at)}
                  </td>
                  <td>
                    <span style={{ color: 'var(--link-color)' }}>{c.user_id}</span>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span style={{ background: 'var(--bg-main)', color: '#00a186', borderRadius: '50%', width: '20px', height: '20px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>
                      →
                    </span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--link-color)' }}>{c.merchant_name || c.merchant_category || '—'}</span>
                  </td>
                  <td>
                    {Number(c.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD
                  </td>
                  <td style={{ maxWidth: '300px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                      {(!c.triggered_rules || c.triggered_rules.length === 0) ? (
                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>—</span>
                      ) : (
                        c.triggered_rules.map((rule, idx) => {
                          const style = getRuleStyle(rule);
                          return (
                            <span key={idx} style={{ 
                              background: style.bg, 
                              color: style.color, 
                              padding: '0.15rem 0.4rem', 
                              borderRadius: '0.25rem', 
                              fontSize: '0.75rem', 
                              fontWeight: 600,
                              whiteSpace: 'nowrap'
                            }}>
                              {rule}
                            </span>
                          );
                        })
                      )}
                    </div>
                  </td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                    {Number(c.final_score || 0).toFixed(6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}