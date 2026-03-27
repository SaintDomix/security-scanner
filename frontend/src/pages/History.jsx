import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { scansAPI, downloadReport } from '../utils/api'
import { formatDistanceToNow } from 'date-fns'
import { Search, Filter, Trash2, Eye, Download, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'

const STATUS_OPTS = ['', 'completed', 'failed', 'running', 'pending']
const MODE_OPTS   = ['', 'full', 'sast', 'secrets', 'dast']

export default function History() {
  const [scans, setScans]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch]   = useState('')
  const [status, setStatus]   = useState('')
  const [mode, setMode]       = useState('')
  const [page, setPage]       = useState(0)
  const PER_PAGE = 15

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: PER_PAGE, offset: page * PER_PAGE }
      if (status) params.status_filter = status
      if (mode)   params.mode_filter   = mode
      if (search) params.search        = search
      const r = await scansAPI.list(params)
      setScans(r.data)
    } catch {}
    finally { setLoading(false) }
  }, [search, status, mode, page])

  useEffect(() => { load() }, [load])

  const del = async (id, e) => {
    e.preventDefault()
    if (!confirm('Delete this scan?')) return
    await scansAPI.delete(id)
    load()
  }

  const statusColor = { completed:'var(--green)', failed:'var(--red)', running:'var(--accent)', pending:'var(--text3)' }
  const statusBg    = { completed:'var(--green-dim)', failed:'var(--red-dim)', running:'var(--accent-glow)', pending:'rgba(100,116,139,0.1)' }

  return (
    <div className="animate-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:700, marginBottom:4 }}>Scan History</h1>
          <p style={{ color:'var(--text3)', fontSize:14 }}>All your security scans</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={14}/> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom:20, padding:'14px 18px' }}>
        <div style={{ display:'flex', gap:12, flexWrap:'wrap', alignItems:'center' }}>
          <div style={{ position:'relative', flex:'1', minWidth:200 }}>
            <Search size={14} style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:'var(--text3)' }}/>
            <input className="input" placeholder="Search by URL or filename…"
              value={search} onChange={e=>{setSearch(e.target.value);setPage(0)}}
              style={{ paddingLeft:32 }}/>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <Filter size={14} style={{ color:'var(--text3)' }}/>
            <select className="input" style={{ width:'auto', paddingRight:32 }}
              value={status} onChange={e=>{setStatus(e.target.value);setPage(0)}}>
              {STATUS_OPTS.map(s=><option key={s} value={s}>{s||'All statuses'}</option>)}
            </select>
            <select className="input" style={{ width:'auto', paddingRight:32 }}
              value={mode} onChange={e=>{setMode(e.target.value);setPage(0)}}>
              {MODE_OPTS.map(m=><option key={m} value={m}>{m||'All modes'}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        <div style={{ overflowX:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:13 }}>
            <thead>
              <tr style={{ borderBottom:'1px solid var(--border)' }}>
                {['ID','Target','Mode','Status','Findings','Critical','Date',''].map(h=>(
                  <th key={h} style={{ padding:'12px 16px', textAlign:'left', fontSize:11,
                    fontWeight:700, color:'var(--text3)', textTransform:'uppercase',
                    letterSpacing:'0.05em', whiteSpace:'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ padding:48, textAlign:'center' }}>
                  <div className="spinner" style={{ margin:'0 auto' }}/>
                </td></tr>
              ) : scans.length === 0 ? (
                <tr><td colSpan={8} style={{ padding:48, textAlign:'center', color:'var(--text3)' }}>
                  No scans found
                </td></tr>
              ) : scans.map(s => (
                <tr key={s.id} style={{ borderBottom:'1px solid var(--border)',
                  transition:'background 0.1s' }}
                  onMouseEnter={e=>e.currentTarget.style.background='var(--surface2)'}
                  onMouseLeave={e=>e.currentTarget.style.background=''}>
                  <td style={{ padding:'12px 16px', color:'var(--text3)', fontFamily:'var(--font-mono)' }}>
                    #{s.id}
                  </td>
                  <td style={{ padding:'12px 16px', maxWidth:260 }}>
                    <div className="truncate" style={{ color:'var(--text)' }}>{s.target}</div>
                  </td>
                  <td style={{ padding:'12px 16px' }}>
                    <span style={{ fontSize:11, fontWeight:600, color:'var(--text2)',
                      background:'var(--surface2)', padding:'2px 7px', borderRadius:4 }}>
                      {s.scan_mode?.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding:'12px 16px' }}>
                    <span style={{ fontSize:11, fontWeight:600, padding:'3px 8px', borderRadius:4,
                      color:statusColor[s.status], background:statusBg[s.status] }}>
                      {s.status}
                    </span>
                  </td>
                  <td style={{ padding:'12px 16px', textAlign:'center' }}>
                    {s.gitleaks_findings + s.semgrep_findings + s.bearer_findings + s.dast_findings}
                  </td>
                  <td style={{ padding:'12px 16px', textAlign:'center' }}>
                    {s.critical_count > 0
                      ? <span className="badge badge-crit">{s.critical_count}</span>
                      : <span style={{ color:'var(--text3)' }}>—</span>}
                  </td>
                  <td style={{ padding:'12px 16px', color:'var(--text3)', whiteSpace:'nowrap' }}>
                    {formatDistanceToNow(new Date(s.created_at), { addSuffix:true })}
                  </td>
                  <td style={{ padding:'12px 16px' }}>
                    <div style={{ display:'flex', gap:6 }}>
                      <Link to={`/scan/${s.id}`} className="btn btn-ghost btn-sm" style={{ padding:'5px 8px' }}>
                        <Eye size={13}/>
                      </Link>
                      {s.status === 'completed' && (
                        <button className="btn btn-ghost btn-sm" style={{ padding:'5px 8px' }}
                          onClick={() => downloadReport(s.id)}>
                          <Download size={13}/>
                        </button>
                      )}
                      <button className="btn btn-danger btn-sm" style={{ padding:'5px 8px' }}
                        onClick={e=>del(s.id,e)}>
                        <Trash2 size={13}/>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
          padding:'12px 16px', borderTop:'1px solid var(--border)' }}>
          <span style={{ fontSize:12, color:'var(--text3)' }}>
            Showing {page*PER_PAGE+1}–{page*PER_PAGE+scans.length}
          </span>
          <div style={{ display:'flex', gap:6 }}>
            <button className="btn btn-ghost btn-sm" disabled={page===0} onClick={()=>setPage(p=>p-1)}>
              <ChevronLeft size={14}/>
            </button>
            <span style={{ padding:'6px 12px', fontSize:13 }}>Page {page+1}</span>
            <button className="btn btn-ghost btn-sm" disabled={scans.length<PER_PAGE}
              onClick={()=>setPage(p=>p+1)}>
              <ChevronRight size={14}/>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
