import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { scansAPI } from '../utils/api'
import { Github, Upload, Search, Shield, AlertCircle, CheckCircle, Info, Lock, Key, Code } from 'lucide-react'

const MODES = [
  { id:'full',    label:'Full Scan',    icon:Shield, desc:'Secrets + SAST (Gitleaks + Semgrep + Bandit)' },
  { id:'secrets', label:'Secrets Only', icon:Key,    desc:'Gitleaks — leaked credentials, tokens, API keys' },
  { id:'sast',    label:'SAST Only',    icon:Code,   desc:'Semgrep + Bandit — code vulnerabilities & privacy' },
]

export default function SastScan() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const fileRef = useRef()

  const [tab, setTab] = useState('url')           // url | upload
  const [url, setUrl] = useState('')
  const [dastUrl, setDastUrl] = useState('')
  const [file, setFile] = useState(null)
  const [mode, setMode] = useState('full')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [validating, setValidating] = useState(false)
  const [ghInfo, setGhInfo] = useState(null)

  const validateUrl = async (val) => {
    setUrl(val); setGhInfo(null)
    if (!val.includes('github.com')) return
    setValidating(true)
    // We rely on backend validation — just show a preview hint
    setTimeout(() => setValidating(false), 600)
  }

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      let res
      if (tab === 'url') {
        if (!url.trim()) { setError('Please enter a GitHub URL'); setLoading(false); return }
        const fd = new FormData()
        fd.append('repo_url', url.trim())
        fd.append('scan_mode', mode)
        if (dastUrl) fd.append('dast_url', dastUrl)
        res = await scansAPI.scanGithub(fd)
      } else {
        if (!file) { setError('Please select a .zip file'); setLoading(false); return }
        const fd = new FormData()
        fd.append('file', file)
        fd.append('scan_mode', mode)
        if (dastUrl) fd.append('dast_url', dastUrl)
        res = await scansAPI.scanUpload(fd)
      }
      navigate(`/scan/${res.data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed to start')
      setLoading(false)
    }
  }

  const isFree = user?.subscription_tier === 'free'

  return (
    <div className="animate-in">
      <div style={{ marginBottom:28 }}>
        <h1 style={{ fontSize:22, fontWeight:700, marginBottom:6 }}>SAST &amp; Secrets Scan</h1>
        <p style={{ color:'var(--text3)', fontSize:14 }}>
          Analyze source code for leaked secrets, vulnerabilities, and privacy issues
        </p>
      </div>

      <form onSubmit={submit}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 380px', gap:24, alignItems:'start' }}
             className="scan-grid">

          {/* Left column */}
          <div style={{ display:'flex', flexDirection:'column', gap:20 }}>

            {/* Tab selector */}
            <div className="card" style={{ padding:20 }}>
              <div className="tabs" style={{ marginBottom:20 }}>
                <button type="button" className={`tab-item${tab==='url'?' active':''}`}
                  onClick={()=>setTab('url')}>
                  <Github size={15}/> GitHub URL
                </button>
                <button type="button" className={`tab-item${tab==='upload'?' active':''}`}
                  onClick={()=>setTab('upload')}>
                  <Upload size={15}/> Upload .zip
                </button>
              </div>

              {tab === 'url' ? (
                <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
                  <div>
                    <label className="form-label">GitHub Repository URL</label>
                    <div style={{ position:'relative' }}>
                      <input className="input" type="url"
                        placeholder="https://github.com/owner/repo"
                        value={url} onChange={e=>validateUrl(e.target.value)} required />
                      {validating && (
                        <div style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)' }}>
                          <div className="spinner" style={{ width:14, height:14 }}/>
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize:11, color:'var(--text3)', marginTop:5 }}>
                      Public repos only unless you set GITHUB_TOKEN in the backend .env
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="form-label">Upload .zip Archive</label>
                  <div
                    onClick={()=>fileRef.current.click()}
                    onDragOver={e=>{e.preventDefault();e.currentTarget.style.borderColor='var(--accent)'}}
                    onDragLeave={e=>e.currentTarget.style.borderColor='var(--border2)'}
                    onDrop={e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f?.name.endsWith('.zip'))setFile(f)}}
                    style={{ border:'2px dashed var(--border2)', borderRadius:'var(--radius)',
                      padding:32, textAlign:'center', cursor:'pointer', transition:'border-color 0.2s',
                      background:'var(--bg2)' }}>
                    <Upload size={28} style={{ color:'var(--text3)', margin:'0 auto 10px' }}/>
                    {file ? (
                      <div>
                        <div style={{ color:'var(--green)', fontWeight:600 }}>{file.name}</div>
                        <div style={{ fontSize:12, color:'var(--text3)', marginTop:4 }}>
                          {(file.size/1024/1024).toFixed(2)} MB
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div style={{ fontWeight:500, marginBottom:4 }}>Drop .zip here or click to browse</div>
                        <div style={{ fontSize:12, color:'var(--text3)' }}>Max 50 MB</div>
                      </div>
                    )}
                    <input ref={fileRef} type="file" accept=".zip" style={{ display:'none' }}
                      onChange={e=>setFile(e.target.files[0])}/>
                  </div>
                </div>
              )}
            </div>

            {/* Scan mode */}
            <div className="card" style={{ padding:20 }}>
              <label className="form-label" style={{ marginBottom:12 }}>Scan Mode</label>
              <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                {MODES.map(m => (
                  <label key={m.id} style={{ display:'flex', alignItems:'center', gap:12, padding:'12px 14px',
                    borderRadius:'var(--radius)', border:`1px solid ${mode===m.id?'var(--accent)':'var(--border)'}`,
                    background: mode===m.id?'var(--surface2)':'transparent',
                    cursor:'pointer', transition:'all 0.15s' }}>
                    <input type="radio" name="mode" value={m.id} checked={mode===m.id}
                      onChange={()=>setMode(m.id)} style={{ accentColor:'var(--accent)' }}/>
                    <m.icon size={16} style={{ color: mode===m.id?'var(--accent)':'var(--text3)', flexShrink:0 }}/>
                    <div>
                      <div style={{ fontSize:13, fontWeight:600 }}>{m.label}</div>
                      <div style={{ fontSize:11, color:'var(--text3)' }}>{m.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Optional DAST URL */}
            <div className="card" style={{ padding:20 }}>
              <label className="form-label" style={{ marginBottom:2 }}>
                Live URL for DAST
                <span style={{ marginLeft:8, fontSize:10, color:'var(--text3)', textTransform:'none', letterSpacing:0 }}>
                  optional — scans HTTP headers, cookies, exposed paths
                </span>
              </label>
              <div style={{ position:'relative' }}>
                <input className="input"
                  placeholder="https://your-deployed-app.com"
                  value={dastUrl} onChange={e=>setDastUrl(e.target.value)}
                  disabled={isFree}
                  style={{ paddingLeft: isFree ? 38 : 14 }}/>
                {isFree && (
                  <Lock size={14} style={{ position:'absolute', left:12, top:'50%', transform:'translateY(-50%)', color:'var(--text3)' }}/>
                )}
              </div>
              {isFree && (
                <div style={{ fontSize:11, color:'var(--text3)', marginTop:5 }}>
                  DAST requires Pro plan
                </div>
              )}
            </div>
          </div>

          {/* Right column — info panel */}
          <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
            <div className="card" style={{ padding:20 }}>
              <h3 style={{ fontSize:14, fontWeight:600, marginBottom:14, color:'var(--text2)' }}>Tools included</h3>
              {[
                { name:'Gitleaks', color:'var(--red)', desc:'Detects API keys, passwords, tokens in git history' },
                { name:'Semgrep', color:'var(--orange)', desc:'SAST — finds code bugs, insecure patterns' },
                { name:'Bandit', color:'var(--purple)', desc:'Privacy & security SAST, CWE detection' },
                { name:'DAST Probe', color:'var(--cyan)', desc:'HTTP header analysis, exposed endpoints', pro:true },
              ].map(t => (
                <div key={t.name} style={{ display:'flex', gap:10, marginBottom:12, opacity: t.pro&&isFree?0.4:1 }}>
                  <div style={{ width:8, height:8, borderRadius:'50%', background:t.color, marginTop:5, flexShrink:0 }}/>
                  <div>
                    <div style={{ fontSize:13, fontWeight:600 }}>
                      {t.name} {t.pro&&<span style={{ fontSize:10, color:'var(--accent)' }}>PRO</span>}
                    </div>
                    <div style={{ fontSize:11, color:'var(--text3)' }}>{t.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="card" style={{ padding:16, background:'rgba(59,130,246,0.05)', borderColor:'rgba(59,130,246,0.2)' }}>
              <div style={{ display:'flex', gap:8 }}>
                <Info size={15} style={{ color:'var(--accent)', flexShrink:0, marginTop:1 }}/>
                <div style={{ fontSize:12, color:'var(--text2)', lineHeight:1.6 }}>
                  Scans run in the background. You'll be redirected to the results page where you can track progress in real-time.
                </div>
              </div>
            </div>

            {error && (
              <div style={{ display:'flex', gap:8, padding:'12px 14px',
                background:'var(--red-dim)', border:'1px solid rgba(239,68,68,0.2)',
                borderRadius:'var(--radius)', color:'var(--red)', fontSize:13 }}>
                <AlertCircle size={15} style={{ flexShrink:0, marginTop:1 }}/> {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary btn-lg" disabled={loading}
              style={{ justifyContent:'center' }}>
              {loading ? <><div className="spinner"/>&nbsp;Starting scan…</> : <><Search size={17}/>&nbsp;Start scan</>}
            </button>
          </div>
        </div>
      </form>

      <style>{`
        @media (max-width: 900px) {
          .scan-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  )
}
