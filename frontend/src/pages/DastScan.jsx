import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { scansAPI } from '../utils/api'
import { Globe, Shield, Lock, AlertCircle, Info, ChevronRight } from 'lucide-react'

const CHECKS = [
  { label:'Security headers', desc:'X-Frame-Options, CSP, HSTS, X-Content-Type-Options…' },
  { label:'Cookie security', desc:'Secure, HttpOnly, SameSite flags' },
  { label:'Information disclosure', desc:'Server version, X-Powered-By leaks' },
  { label:'Exposed sensitive paths', desc:'.env, .git/config, admin panels, phpinfo' },
  { label:'Transport security', desc:'HTTP vs HTTPS, mixed content' },
  { label:'ZAP integration', desc:'Full spider + active scan (if ZAP installed)' },
]

export default function DastScan() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isPro = user?.subscription_tier !== 'free'

  const submit = async e => {
    e.preventDefault()
    if (!isPro) return
    if (!url.startsWith('http')) { setError('URL must start with http:// or https://'); return }
    setLoading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('target_url', url.trim())
      const res = await scansAPI.scanDast(fd)
      navigate(`/scan/${res.data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'DAST scan failed to start')
      setLoading(false)
    }
  }

  return (
    <div className="animate-in">
      <div style={{ marginBottom:28 }}>
        <h1 style={{ fontSize:22, fontWeight:700, marginBottom:6 }}>DAST Scan</h1>
        <p style={{ color:'var(--text3)', fontSize:14 }}>
          Dynamic Application Security Testing — scan a live running web application
        </p>
      </div>

      {!isPro && (
        <div style={{ marginBottom:24, padding:'16px 20px',
          background:'rgba(139,92,246,0.08)', border:'1px solid rgba(139,92,246,0.25)',
          borderRadius:'var(--radius-lg)', display:'flex', alignItems:'center', gap:14 }}>
          <div style={{ width:40, height:40, borderRadius:10, background:'rgba(139,92,246,0.15)',
            display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
            <Lock size={20} style={{ color:'var(--purple)' }}/>
          </div>
          <div style={{ flex:1 }}>
            <div style={{ fontWeight:600, marginBottom:3 }}>Pro feature</div>
            <div style={{ fontSize:13, color:'var(--text3)' }}>
              DAST scanning is available on Pro and Enterprise plans
            </div>
          </div>
          <Link to="/pricing" className="btn btn-primary btn-sm">
            Upgrade <ChevronRight size={14}/>
          </Link>
        </div>
      )}

      <div style={{ display:'grid', gridTemplateColumns:'1fr 360px', gap:24, alignItems:'start' }}
           className="dast-grid">

        <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
          <div className="card" style={{ padding:24 }}>
            <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:20 }}>
              <div>
                <label className="form-label">Target URL</label>
                <input className="input" type="url"
                  placeholder="https://your-app.example.com"
                  value={url} onChange={e=>setUrl(e.target.value)}
                  disabled={!isPro} required />
                <div style={{ fontSize:11, color:'var(--text3)', marginTop:5 }}>
                  The server must be reachable from the machine running the backend
                </div>
              </div>

              {error && (
                <div style={{ display:'flex', gap:8, padding:'12px 14px',
                  background:'var(--red-dim)', border:'1px solid rgba(239,68,68,0.2)',
                  borderRadius:'var(--radius)', color:'var(--red)', fontSize:13 }}>
                  <AlertCircle size={15} style={{ flexShrink:0, marginTop:1 }}/> {error}
                </div>
              )}

              <button type="submit" className="btn btn-primary btn-lg" disabled={loading || !isPro}
                style={{ justifyContent:'center' }}>
                {loading
                  ? <><div className="spinner"/>&nbsp;Starting…</>
                  : <><Globe size={17}/>&nbsp;{isPro ? 'Start DAST scan' : 'Upgrade to scan'}</>}
              </button>
            </form>
          </div>

          {/* What it checks */}
          <div className="card" style={{ padding:20 }}>
            <h3 style={{ fontSize:14, fontWeight:600, marginBottom:14 }}>What gets checked</h3>
            <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
              {CHECKS.map(c => (
                <div key={c.label} style={{ display:'flex', gap:10 }}>
                  <div style={{ width:6, height:6, borderRadius:'50%', background:'var(--purple)',
                    marginTop:6, flexShrink:0 }}/>
                  <div>
                    <div style={{ fontSize:13, fontWeight:500 }}>{c.label}</div>
                    <div style={{ fontSize:11, color:'var(--text3)' }}>{c.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Info sidebar */}
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card" style={{ padding:20 }}>
            <h3 style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>How it works</h3>
            {[
              { step:'1', text:'Enter the URL of your running app' },
              { step:'2', text:'We send probe HTTP requests to check security headers' },
              { step:'3', text:'We test known sensitive paths (.env, .git, admin)' },
              { step:'4', text:'Cookie and transport security are verified' },
              { step:'5', text:'Full PDF report generated with findings + fixes' },
            ].map(s => (
              <div key={s.step} style={{ display:'flex', gap:10, marginBottom:10 }}>
                <div style={{ width:22, height:22, borderRadius:'50%', background:'var(--surface2)',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  fontSize:11, fontWeight:700, color:'var(--accent)', flexShrink:0 }}>
                  {s.step}
                </div>
                <div style={{ fontSize:13, color:'var(--text2)', paddingTop:2 }}>{s.text}</div>
              </div>
            ))}
          </div>

          <div className="card" style={{ padding:16, background:'rgba(245,158,11,0.05)', borderColor:'rgba(245,158,11,0.2)' }}>
            <div style={{ display:'flex', gap:8 }}>
              <Info size={15} style={{ color:'var(--orange)', flexShrink:0, marginTop:1 }}/>
              <div style={{ fontSize:12, color:'var(--text2)', lineHeight:1.6 }}>
                Only scan applications you own or have explicit permission to test.
                Unauthorized scanning may violate laws and terms of service.
              </div>
            </div>
          </div>

          
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .dast-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}
