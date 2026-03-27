import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { scansAPI, downloadReport } from '../utils/api'
import api from '../utils/api'
import { formatDistanceToNow, format } from 'date-fns'
import {
  ArrowLeft, Download, RefreshCw, CheckCircle, XCircle, Clock,
  Key, Code, Shield, Globe, Star, GitBranch, AlertTriangle,
  ChevronDown, ChevronRight, ExternalLink
} from 'lucide-react'

function SevBadge({ sev }) {
  const map = { critical:'badge-crit', high:'badge-high', medium:'badge-med', low:'badge-low' }
  return <span className={`badge ${map[sev]||'badge-gray'}`}>{sev}</span>
}

function DownloadBtn({ scanId, label }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr]   = useState('')
  const handle = async () => {
    setBusy(true); setErr('')
    try { await downloadReport(scanId) }
    catch (e) { setErr('Download failed') }
    finally { setBusy(false) }
  }
  return (
    <span style={{ display:'inline-flex', flexDirection:'column', alignItems:'flex-end', gap:4 }}>
      <button className="btn btn-primary btn-sm" onClick={handle} disabled={busy}>
        {busy
          ? <><div className="spinner" style={{width:13,height:13,borderTopColor:'#fff'}}/>&nbsp;Downloading…</>
          : <><Download size={14}/>&nbsp;{label}</>}
      </button>
      {err && <span style={{ fontSize:11, color:'var(--red)' }}>{err}</span>}
    </span>
  )
}

function ToolSection({ icon: Icon, title, count, color, findings }) {
  const [open, setOpen] = useState(count > 0)
  const [expanded, setExpanded] = useState({})
  if (findings === undefined) return null

  return (
    <div className="card" style={{ marginBottom:12, padding:0, overflow:'hidden' }}>
      <button onClick={() => setOpen(o=>!o)}
        style={{ width:'100%', padding:'16px 20px', background:'none', border:'none',
          cursor:'pointer', display:'flex', alignItems:'center', gap:12, textAlign:'left' }}>
        <div style={{ width:36, height:36, borderRadius:8, background:`${color}22`,
          display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
          <Icon size={18} style={{ color }}/>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:14, fontWeight:600, color:'var(--text)' }}>{title}</div>
          <div style={{ fontSize:12, color:'var(--text3)' }}>{count} finding{count!==1?'s':''}</div>
        </div>
        {count === 0
          ? <span className="badge badge-green">Clean</span>
          : <span className="badge badge-high">{count}</span>}
        {open ? <ChevronDown size={16} style={{color:'var(--text3)'}}/> : <ChevronRight size={16} style={{color:'var(--text3)'}}/>}
      </button>

      {open && (
        <div style={{ borderTop:'1px solid var(--border)', padding:'0 20px 16px' }}>
          {findings.length === 0 ? (
            <div style={{ padding:'24px 0', textAlign:'center', color:'var(--green)', fontSize:13 }}>
              <CheckCircle size={20} style={{ margin:'0 auto 8px' }}/> No issues found
            </div>
          ) : (
            findings.slice(0, 50).map((f, i) => (
              <div key={i} style={{ borderBottom:'1px solid var(--border)', padding:'10px 0' }}>
                <div style={{ display:'flex', alignItems:'flex-start', gap:8, marginBottom:4 }}>
                  <SevBadge sev={f.severity || 'low'}/>
                  <div style={{ flex:1, fontSize:13, fontWeight:500, color:'var(--text)' }}>
                    {f.title || f.rule_id || f.message || f.description || 'Finding'}
                  </div>
                  <button onClick={()=>setExpanded(p=>({...p,[i]:!p[i]}))}
                    style={{ background:'none', border:'none', cursor:'pointer', color:'var(--text3)', padding:2 }}>
                    {expanded[i]?<ChevronDown size={13}/>:<ChevronRight size={13}/>}
                  </button>
                </div>
                {(f.file || f.line) && (
                  <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--font-mono)' }}>
                    {f.file && <span style={{ color:'var(--cyan)' }}>{f.file}</span>}
                    {f.line && <span>:{f.line}</span>}
                  </div>
                )}
                {expanded[i] && (
                  <div style={{ marginTop:8, padding:'8px 12px', background:'var(--bg2)',
                    borderRadius:'var(--radius)', fontSize:12, color:'var(--text2)', lineHeight:1.6 }}>
                    {f.message     && <div><b>Message:</b> {f.message}</div>}
                    {f.description && <div><b>Description:</b> {f.description}</div>}
                    {f.solution    && <div style={{marginTop:4}}><b>Fix:</b> {f.solution}</div>}
                    {f.evidence    && <div style={{marginTop:4,fontFamily:'var(--font-mono)',fontSize:11,color:'var(--text3)'}}><b>Evidence:</b> {f.evidence}</div>}
                    {f.cwe_ids     && f.cwe_ids !== "None" && f.cwe_ids !== "" && <div style={{marginTop:4}}><b>CWE:</b> {f.cwe_ids}</div>}
                    {f.more_info   && <div style={{marginTop:4}}><a href={f.more_info} target="_blank" rel="noreferrer" style={{fontSize:11}}>More info ↗</a></div>}
                    {f.commit      && <div style={{marginTop:4,fontFamily:'var(--font-mono)',fontSize:11}}><b>Commit:</b> {f.commit}</div>}
                  </div>
                )}
              </div>
            ))
          )}
          {findings.length > 50 && (
            <div style={{ padding:'10px 0', fontSize:12, color:'var(--text3)', textAlign:'center' }}>
              +{findings.length - 50} more findings — see PDF report
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ScanDetail() {
  const { id } = useParams()
  const [scan, setScan]         = useState(null)
  const [findings, setFindings] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  const fetchScan = useCallback(async () => {
    try {
      const r = await scansAPI.get(id)
      setScan(r.data)
    } catch {
      setError('Scan not found')
    } finally {
      setLoading(false)
    }
  }, [id])

  // Load findings separately once scan completes
  const fetchFindings = useCallback(async () => {
    try {
      const r = await api.get(`/scans/${id}/findings`)
      setFindings(r.data)
    } catch {
      setFindings({ gitleaks:[], semgrep:[], bandit:[], dast:[] })
    }
  }, [id])

  useEffect(() => { fetchScan() }, [fetchScan])

  // Poll while running/pending
  useEffect(() => {
    if (!scan) return
    if (scan.status === 'completed' || scan.status === 'failed') {
      if (scan.status === 'completed' && !findings) fetchFindings()
      return
    }
    const t = setInterval(fetchScan, 3000)
    return () => clearInterval(t)
  }, [scan, findings, fetchScan, fetchFindings])

  if (loading) return (
    <div style={{ display:'flex', justifyContent:'center', padding:80 }}>
      <div className="spinner" style={{ width:32, height:32 }}/>
    </div>
  )
  if (error || !scan) return (
    <div className="empty-state">
      <XCircle size={40}/>
      <h3>{error || 'Scan not found'}</h3>
      <Link to="/history" className="btn btn-ghost btn-sm" style={{ marginTop:12 }}>← Back</Link>
    </div>
  )

  const total = scan.gitleaks_findings + scan.semgrep_findings + scan.bearer_findings + scan.dast_findings
  const statusIcon = {
    completed: <CheckCircle size={18} style={{color:'var(--green)'}}/>,
    failed:    <XCircle size={18} style={{color:'var(--red)'}}/>,
    running:   <div className="spinner" style={{width:18,height:18}}/>,
    pending:   <Clock size={18} style={{color:'var(--text3)'}}/>
  }

  const gl  = findings?.gitleaks || []
  const sem = findings?.semgrep  || []
  const ban = findings?.bandit   || []
  const dst = findings?.dast     || []

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ display:'flex', alignItems:'flex-start', gap:16, marginBottom:28 }}>
        <Link to="/history" style={{ color:'var(--text3)', marginTop:4 }}>
          <ArrowLeft size={20}/>
        </Link>
        <div style={{ flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:6, flexWrap:'wrap' }}>
            {statusIcon[scan.status]}
            <h1 style={{ fontSize:18, fontWeight:700 }}>Scan #{scan.id}</h1>
            <span style={{ fontSize:12, color:'var(--text3)', background:'var(--surface2)',
              padding:'2px 8px', borderRadius:4, fontFamily:'var(--font-mono)' }}>
              {scan.scan_mode?.toUpperCase()}
            </span>
          </div>
          <div className="truncate" style={{ fontSize:13, color:'var(--text3)', maxWidth:600 }}>
            {scan.target}
          </div>
          <div style={{ fontSize:12, color:'var(--text3)', marginTop:4 }}>
            {format(new Date(scan.created_at), 'PPpp')}
            {scan.completed_at && ` · Completed ${formatDistanceToNow(new Date(scan.completed_at), {addSuffix:true})}`}
          </div>
        </div>
        <div style={{ display:'flex', gap:8, flexShrink:0 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => { fetchScan(); if(scan.status==='completed') fetchFindings() }}>
            <RefreshCw size={14}/> Refresh
          </button>
          {scan.status === 'completed' && <DownloadBtn scanId={scan.id} label="PDF Report"/>}
        </div>
      </div>

      {/* GitHub info */}
      {scan.github_valid && (
        <div className="card" style={{ marginBottom:20, padding:'14px 20px' }}>
          <div style={{ display:'flex', alignItems:'center', gap:16, flexWrap:'wrap' }}>
            <GitBranch size={16} style={{color:'var(--text3)'}}/>
            <a href={scan.target} target="_blank" rel="noreferrer"
              style={{ fontSize:13, fontWeight:500, display:'flex', alignItems:'center', gap:4 }}>
              {scan.target} <ExternalLink size={12}/>
            </a>
            {scan.github_stars !== null && (
              <div style={{ display:'flex', alignItems:'center', gap:4, fontSize:13, color:'var(--text3)' }}>
                <Star size={13} style={{color:'var(--orange)'}}/> {scan.github_stars}
              </div>
            )}
            {scan.github_language && <span style={{ fontSize:12, color:'var(--cyan)' }}>{scan.github_language}</span>}
            {scan.github_description && <span style={{ fontSize:12, color:'var(--text3)', flex:1 }}>{scan.github_description}</span>}
          </div>
        </div>
      )}

      {/* Running state */}
      {(scan.status === 'running' || scan.status === 'pending') && (
        <div className="card" style={{ marginBottom:20, padding:24, textAlign:'center' }}>
          <div style={{ position:'relative', width:80, height:80, margin:'0 auto 16px' }}>
            <div style={{ width:80, height:80, borderRadius:'50%', border:'3px solid var(--border2)',
              borderTopColor:'var(--accent)', animation:'spin 1s linear infinite' }}/>
            <Shield size={28} style={{ position:'absolute', top:'50%', left:'50%',
              transform:'translate(-50%,-50%)', color:'var(--accent)' }}/>
          </div>
          <div style={{ fontSize:16, fontWeight:600, marginBottom:6 }}>
            {scan.status === 'pending' ? 'Scan queued…' : 'Scanning in progress…'}
          </div>
          <div style={{ fontSize:13, color:'var(--text3)' }}>Auto-refreshing every 3 seconds.</div>
        </div>
      )}

      {/* Summary cards */}
      {scan.status === 'completed' && (
        <>
          <div className="grid-4" style={{ marginBottom:20 }}>
            {[
              { label:'Critical', val:scan.critical_count, color:'var(--crit)' },
              { label:'High',     val:scan.high_count,     color:'var(--high)' },
              { label:'Medium',   val:scan.medium_count,   color:'var(--med)'  },
              { label:'Low',      val:scan.low_count,      color:'var(--low)'  },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign:'center', padding:'18px 12px' }}>
                <div style={{ fontSize:32, fontWeight:700, color:s.color, lineHeight:1 }}>{s.val}</div>
                <div style={{ fontSize:12, color:'var(--text3)', marginTop:6 }}>{s.label}</div>
              </div>
            ))}
          </div>

          <div style={{ marginBottom:16, display:'flex', gap:12, flexWrap:'wrap' }}>
            {[
              { label:'Gitleaks', val:scan.gitleaks_findings, color:'var(--red)'    },
              { label:'Semgrep',  val:scan.semgrep_findings,  color:'var(--orange)' },
              { label:'Bandit',   val:scan.bearer_findings,   color:'var(--purple)' },
              { label:'DAST',     val:scan.dast_findings,     color:'var(--cyan)'   },
            ].map(t => (
              <div key={t.label} style={{ padding:'6px 14px', background:'var(--surface)',
                border:'1px solid var(--border)', borderRadius:6, fontSize:13 }}>
                <span style={{color:'var(--text3)'}}>{t.label}: </span>
                <span style={{ fontWeight:700, color:t.val>0?t.color:'var(--green)' }}>{t.val}</span>
              </div>
            ))}
          </div>

          {/* Tool sections with real findings */}
          {findings === null ? (
            <div style={{ textAlign:'center', padding:32 }}>
              <div className="spinner" style={{ margin:'0 auto 12px' }}/>
              <div style={{ fontSize:13, color:'var(--text3)' }}>Loading findings…</div>
            </div>
          ) : (
            <div>
              <h2 style={{ fontSize:16, fontWeight:600, marginBottom:12 }}>Findings by tool</h2>
              <ToolSection icon={Key}    title="Gitleaks — Secret Detection" color="var(--red)"    count={scan.gitleaks_findings} findings={gl}  />
              <ToolSection icon={Code}   title="Semgrep — Static Analysis"   color="var(--orange)" count={scan.semgrep_findings}  findings={sem} />
              <ToolSection icon={Shield} title="Bandit — Python SAST"        color="var(--purple)" count={scan.bearer_findings}   findings={ban} />
              <ToolSection icon={Globe}  title="DAST — Dynamic Analysis"     color="var(--cyan)"   count={scan.dast_findings}     findings={dst} />

              <div style={{ marginTop:20, padding:'16px 20px', background:'var(--surface)',
                border:'1px solid var(--border)', borderRadius:'var(--radius-lg)',
                display:'flex', alignItems:'center', gap:16 }}>
                <Download size={20} style={{color:'var(--accent)'}}/>
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:600, marginBottom:2 }}>Full PDF Report</div>
                  <div style={{ fontSize:12, color:'var(--text3)' }}>
                    Complete findings with file paths, line numbers, and remediation guidance
                  </div>
                </div>
                <DownloadBtn scanId={scan.id} label="Download PDF"/>
              </div>
            </div>
          )}
        </>
      )}

      {scan.status === 'failed' && scan.error_message && (
        <div className="card" style={{ borderColor:'rgba(239,68,68,0.3)', background:'var(--red-dim)', padding:20 }}>
          <div style={{ display:'flex', gap:10, color:'var(--red)' }}>
            <AlertTriangle size={18} style={{flexShrink:0}}/>
            <div>
              <div style={{ fontWeight:600, marginBottom:4 }}>Scan failed</div>
              <div style={{ fontSize:13 }}>{scan.error_message}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
