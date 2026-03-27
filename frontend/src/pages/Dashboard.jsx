import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { scansAPI } from '../utils/api'
import { Shield, Search, Globe, TrendingUp, AlertTriangle, CheckCircle, Clock, ArrowRight, Zap } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const LIMITS = { free: 3, pro: 50, enterprise: 9999 }

function StatCard({ icon: Icon, label, value, color = 'var(--accent)', sub }) {
  return (
    <div className="card" style={{ display:'flex', flexDirection:'column', gap:8 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
        <div style={{ fontSize:13, color:'var(--text3)', fontWeight:500 }}>{label}</div>
        <div style={{ width:32, height:32, borderRadius:8, background:`${color}22`,
          display:'flex', alignItems:'center', justifyContent:'center' }}>
          <Icon size={16} style={{ color }} />
        </div>
      </div>
      <div style={{ fontSize:28, fontWeight:700, color:'var(--text)', lineHeight:1 }}>{value}</div>
      {sub && <div style={{ fontSize:12, color:'var(--text3)' }}>{sub}</div>}
    </div>
  )
}

function ScanRow({ scan }) {
  const statusColor = { completed:'var(--green)', failed:'var(--red)', running:'var(--accent)', pending:'var(--text3)' }
  const total = scan.gitleaks_findings + scan.semgrep_findings + scan.bearer_findings + scan.dast_findings
  return (
    <Link to={`/scan/${scan.id}`} style={{ textDecoration:'none' }}>
      <div style={{ display:'flex', alignItems:'center', gap:12, padding:'12px 0',
        borderBottom:'1px solid var(--border)', cursor:'pointer', transition:'background 0.15s' }}
        onMouseEnter={e=>e.currentTarget.style.background='var(--surface2)'}
        onMouseLeave={e=>e.currentTarget.style.background=''}>
        <div style={{ width:8, height:8, borderRadius:'50%', background:statusColor[scan.status], flexShrink:0,
          boxShadow: scan.status==='running'?`0 0 8px ${statusColor[scan.status]}`:undefined }}/>
        <div style={{ flex:1, minWidth:0 }}>
          <div className="truncate" style={{ fontSize:13, fontWeight:500, color:'var(--text)', marginBottom:2 }}>
            {scan.target}
          </div>
          <div style={{ fontSize:11, color:'var(--text3)' }}>
            {scan.scan_mode?.toUpperCase()} • {formatDistanceToNow(new Date(scan.created_at), { addSuffix:true })}
          </div>
        </div>
        {total > 0 && (
          <div style={{ display:'flex', gap:4 }}>
            {scan.critical_count > 0 && <span className="badge badge-crit">{scan.critical_count}</span>}
            {scan.high_count > 0 && <span className="badge badge-high">{scan.high_count}</span>}
          </div>
        )}
        <ArrowRight size={14} style={{ color:'var(--text3)', flexShrink:0 }}/>
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    scansAPI.list({ limit:10 }).then(r => setScans(r.data)).catch(()=>{}).finally(()=>setLoading(false))
  }, [])

  const completed = scans.filter(s=>s.status==='completed')
  const totalFindings = completed.reduce((a,s)=>a+s.gitleaks_findings+s.semgrep_findings+s.bearer_findings+s.dast_findings,0)
  const critCount = completed.reduce((a,s)=>a+s.critical_count,0)
  const limit = LIMITS[user?.subscription_tier] || 3
  const pct = Math.min((user?.scans_today||0) / limit * 100, 100)

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom:32 }}>
        <h1 style={{ fontSize:24, fontWeight:700, marginBottom:6 }}>
          Good day, {user?.full_name || user?.username} 👋
        </h1>
        <p style={{ color:'var(--text3)', fontSize:14 }}>
          Your security scanning dashboard
        </p>
      </div>

      {/* Usage bar */}
      <div className="card" style={{ marginBottom:24, padding:'16px 20px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <Zap size={15} style={{ color:'var(--accent)' }}/>
            <span style={{ fontSize:13, fontWeight:600 }}>Daily scans</span>
          </div>
          <span style={{ fontSize:13, color:'var(--text3)' }}>
            {user?.scans_today || 0} / {limit === 9999 ? '∞' : limit}
          </span>
        </div>
        <div style={{ height:6, background:'var(--border)', borderRadius:3, overflow:'hidden' }}>
          <div style={{ height:'100%', width:`${pct}%`, borderRadius:3,
            background: pct>85?'var(--red)':pct>60?'var(--orange)':'var(--accent)',
            transition:'width 0.5s ease' }}/>
        </div>
        {pct >= 100 && (
          <div style={{ marginTop:8, fontSize:12, color:'var(--red)' }}>
            Limit reached · <Link to="/pricing">Upgrade for more scans</Link>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid-4" style={{ marginBottom:24 }}>
        <StatCard icon={Search} label="Total Scans" value={scans.length} color="var(--accent)" />
        <StatCard icon={TrendingUp} label="Total Findings" value={totalFindings} color="var(--orange)" />
        <StatCard icon={AlertTriangle} label="Critical" value={critCount}
          color="var(--crit)" sub={critCount>0?'Needs attention':''}/>
        <StatCard icon={CheckCircle} label="Completed" value={completed.length}
          color="var(--green)" sub={`${scans.filter(s=>s.status==='failed').length} failed`}/>
      </div>

      {/* Quick actions */}
      <div style={{ marginBottom:24 }}>
        <h2 style={{ fontSize:16, fontWeight:600, marginBottom:12 }}>Quick scan</h2>
        <div className="grid-2">
          <Link to="/scan/sast" style={{ textDecoration:'none' }}>
            <div className="card" style={{ cursor:'pointer', transition:'all 0.2s',
              borderColor:'transparent', background:'var(--surface)' }}
              onMouseEnter={e=>{e.currentTarget.style.borderColor='var(--accent)';e.currentTarget.style.background='var(--surface2)'}}
              onMouseLeave={e=>{e.currentTarget.style.borderColor='transparent';e.currentTarget.style.background='var(--surface)'}}>
              <div style={{ display:'flex', alignItems:'center', gap:14 }}>
                <div style={{ width:44, height:44, borderRadius:10, background:'rgba(59,130,246,0.1)',
                  display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                  <Search size={22} style={{ color:'var(--accent)' }}/>
                </div>
                <div>
                  <div style={{ fontWeight:600, marginBottom:3 }}>SAST / Secrets Scan</div>
                  <div style={{ fontSize:12, color:'var(--text3)' }}>Gitleaks · Semgrep · Bearer — GitHub URL or .zip upload</div>
                </div>
              </div>
            </div>
          </Link>
          <Link to="/scan/dast" style={{ textDecoration:'none' }}>
            <div className="card" style={{ cursor:'pointer', transition:'all 0.2s',
              borderColor:'transparent', background:'var(--surface)' }}
              onMouseEnter={e=>{e.currentTarget.style.borderColor='var(--purple)';e.currentTarget.style.background='var(--surface2)'}}
              onMouseLeave={e=>{e.currentTarget.style.borderColor='transparent';e.currentTarget.style.background='var(--surface)'}}>
              <div style={{ display:'flex', alignItems:'center', gap:14 }}>
                <div style={{ width:44, height:44, borderRadius:10, background:'rgba(139,92,246,0.1)',
                  display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                  <Globe size={22} style={{ color:'var(--purple)' }}/>
                </div>
                <div>
                  <div style={{ fontWeight:600, marginBottom:3 }}>DAST Scan
                    <span style={{ marginLeft:8, fontSize:11, color:'var(--accent)',
                      background:'var(--accent-glow)', padding:'1px 6px', borderRadius:3 }}>PRO</span>
                  </div>
                  <div style={{ fontSize:12, color:'var(--text3)' }}>Live HTTP scanning — security headers, cookies, exposed paths</div>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent scans */}
      <div className="card">
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
          <h2 style={{ fontSize:16, fontWeight:600 }}>Recent scans</h2>
          <Link to="/history" className="btn btn-ghost btn-sm">View all</Link>
        </div>

        {loading ? (
          <div style={{ textAlign:'center', padding:40 }}><div className="spinner" style={{ margin:'0 auto' }}/></div>
        ) : scans.length === 0 ? (
          <div className="empty-state">
            <Shield size={40}/>
            <h3>No scans yet</h3>
            <p>Run your first scan to see results here</p>
          </div>
        ) : (
          scans.slice(0,8).map(s => <ScanRow key={s.id} scan={s}/>)
        )}
      </div>
    </div>
  )
}
