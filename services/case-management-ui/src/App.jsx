import { useState, useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Link, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CaseDetail from './pages/CaseDetail'
import Charts from './pages/Charts'

export const API = '/api/v1'

export function useStats() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    fetch(`${API}/stats`).then(r => r.json()).then(setStats).catch(() => {})
  }, [])
  return stats
}

export function useLiveCases(filter = '', page = 1) {
  const [cases,   setCases]   = useState([])
  const [limit]               = useState(50)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)

  const filterToDecision = filter === 'BLOCK' ? 'BLOCK,CONFIRMED_FRAUD' : filter

  const fetchCases = useCallback((p) => {
    setLoading(true)
    const offset = (p - 1) * limit
    const qs = new URLSearchParams({ limit, offset, ...(filterToDecision ? { decision: filterToDecision } : {}) }).toString()
    fetch(`${API}/cases?${qs}`)
      .then(r => r.json())
      .then(data => { setCases(data); setHasMore(data.length === limit); setLoading(false) })
      .catch(() => setLoading(false))
  }, [filterToDecision, limit])

  useEffect(() => {
    fetchCases(page)
  }, [fetchCases, page])

  return { cases, hasMore, loading }
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light')
  const [showHeader, setShowHeader] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      if (currentScrollY > lastScrollY && currentScrollY > 60) {
        setShowHeader(false);
      } else {
        setShowHeader(true);
      }
      setLastScrollY(currentScrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  return (
    <BrowserRouter>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        :root {
          --bg-main: #f8f9fa;
          --text-main: #212529;
          --text-muted: #6c757d;
          --text-light: #8c98a4;
          --bg-card: #fff;
          --border-color: #e7eaf3;
          --bg-header: #fff;
          --link-color: #0784c3;
          --link-hover: #045a8b;
          --th-bg: #f8f9fa;
          --bg-active: #f8fbff;
          --brand-bg: #23325b;
          --brand-text: #23325b;
          --map-empty: #e9ecef;
        }

        [data-theme="dark"] {
          --bg-main: #111111;
          --text-main: #e9ecef;
          --text-muted: #adb5bd;
          --text-light: #8c98a4;
          --bg-card: #1c1c1c;
          --border-color: #333333;
          --bg-header: #1c1c1c;
          --link-color: #4da3ff;
          --link-hover: #73bfff;
          --th-bg: #222222;
          --bg-active: #2b3a4a;
          --brand-bg: #4da3ff;
          --brand-text: #4da3ff;
          --map-empty: #2c2c2c;
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        
        body { 
          font-family: 'Inter', sans-serif; 
          background: var(--bg-main); 
          color: var(--text-main); 
          -webkit-font-smoothing: antialiased;
          transition: background 0.2s ease, color 0.2s ease;
          overflow-y: scroll;
        }

        a {
          color: var(--link-color);
          text-decoration: none;
          transition: color 0.2s ease;
        }
        
        a:hover {
          color: var(--link-hover);
        }

        .container {
          max-width: 1320px;
          margin: 0 auto;
          padding: 0 15px;
        }

        .card {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 0.5rem;
          box-shadow: 0 0.5rem 1.2rem rgba(0, 0, 0, 0.05);
          transition: background 0.2s ease, border-color 0.2s ease;
        }
          
        .table-responsive {
          overflow-x: auto;
        }
          
        table {
          width: 100%;
          border-collapse: collapse;
        }
        
        th {
          font-size: 0.8125rem;
          color: var(--text-muted);
          font-weight: 600;
          text-align: left;
          padding: 0.75rem;
          border-bottom: 2px solid var(--border-color);
          background-color: var(--th-bg);
          transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
        }
          
        td {
          padding: 0.75rem;
          font-size: 0.875rem;
          border-bottom: 1px solid var(--border-color);
          vertical-align: middle;
          transition: border-color 0.2s ease;
        }

        tr:last-child td {
          border-bottom: none;
        }
          
        .badge {
          padding: 0.35em 0.65em;
          font-size: 0.75em;
          font-weight: 700;
          line-height: 1;
          color: #fff;
          text-align: center;
          white-space: nowrap;
          vertical-align: baseline;
          border-radius: 0.375rem;
        }
          
        .badge-success { background-color: #00a186; color: #fff; }
        .badge-warning { background-color: #f5c200; color: #fff; }
        .badge-danger { background-color: #e82646; color: #fff; }
        .badge-secondary { background-color: #6c757d; color: #fff; }
      `}</style>

      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <header style={{
          background: 'var(--bg-header)',
          borderBottom: `1px solid var(--border-color)`,
          padding: '1rem 0',
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          transform: showHeader ? 'translateY(0)' : 'translateY(-100%)',
          transition: 'transform 0.3s ease, background 0.2s ease, border-color 0.2s ease'
        }}>
          <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
              <div style={{
                width: 32, height: 32, borderRadius: '50%',
                background: 'var(--brand-bg)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'background 0.2s ease'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M3 3v18h18"/>
                  <path d="M18 9l-5-5-4 4-5-5"/>
                </svg>
              </div>
              <span style={{ fontWeight: 700, fontSize: '1.25rem', color: 'var(--brand-text)' }}>
                FraudScan
              </span>
            </Link>

            <nav style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', fontSize: '0.9375rem', fontWeight: 500 }}>
              <NavLink to="/" style={({ isActive }) => ({ color: isActive ? 'var(--link-color)' : 'var(--text-muted)', textDecoration: 'none' })} end>Home</NavLink>
              <NavLink to="/charts" style={({ isActive }) => ({ color: isActive ? 'var(--link-color)' : 'var(--text-muted)', textDecoration: 'none' })}>Charts & Stats</NavLink>
              <span style={{ color: 'var(--border-color)' }}>|</span>
              <button 
                onClick={toggleTheme} 
                style={{ 
                  background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-main)', 
                  display: 'flex', alignItems: 'center', padding: '0.25rem' 
                }}
                title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
              >
                {theme === 'light' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
                )}
              </button>
            </nav>
          </div>
        </header>

        <main className="main-content" style={{ flex: 1, padding: '2rem 0', animation: 'fadeIn 0.3s ease' }}>
          <style>{`
            @keyframes fadeIn {
              from { opacity: 0; }
              to { opacity: 1; }
            }
          `}</style>
          <div className="container">
            <Routes>
              <Route path="/"          element={<Dashboard />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/charts"    element={<Charts />} />
            </Routes>
          </div>
        </main>
        
        <footer style={{ background: 'var(--th-bg)', padding: '2rem 0', borderTop: '1px solid var(--border-color)', marginTop: 'auto', transition: 'background 0.2s ease, border-color 0.2s ease' }}>
          <div className="container" style={{ fontSize: '0.875rem', color: 'var(--text-muted)', textAlign: 'center', transition: 'color 0.2s ease' }}>
            Powered by FraudScan © 2026
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}