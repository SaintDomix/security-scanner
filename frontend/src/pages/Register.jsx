import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email:'', username:'', full_name:'', password:'' })
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async e => {
    e.preventDefault()
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return }
    setLoading(true); setError('')
    try {
      await register(form)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight:'100vh', background:'var(--bg)',
      display:'flex', alignItems:'center', justifyContent:'center', padding:24
    }}>
      <div style={{
        position:'fixed', inset:0, opacity:0.03,
        backgroundImage:'linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px)',
        backgroundSize:'40px 40px', pointerEvents:'none'
      }}/>

      <div className="animate-in" style={{ width:'100%', maxWidth:440 }}>
        <div style={{ textAlign:'center', marginBottom:32 }}>
          <div style={{
            width:56, height:56, borderRadius:14, margin:'0 auto 16px',
            background:'linear-gradient(135deg,#3B82F6,#1D4ED8)',
            display:'flex', alignItems:'center', justifyContent:'center',
            boxShadow:'0 8px 32px rgba(59,130,246,0.4)'
          }}>
            <Shield size={28} color="#fff"/>
          </div>
          <h1 style={{ fontSize:26, fontWeight:700, color:'var(--text)', marginBottom:6 }}>Create account</h1>
          <p style={{ color:'var(--text3)', fontSize:14 }}>Start scanning for free — 3 scans/day</p>
        </div>

        <div className="card" style={{ padding:32 }}>
          <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:18 }}>
            <div className="grid-2">
              <div>
                <label className="form-label">Full Name</label>
                <input className="input" placeholder="Jane Doe"
                  value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/>
              </div>
              <div>
                <label className="form-label">Username</label>
                <input className="input" placeholder="janedoe" required
                  value={form.username} onChange={e=>setForm({...form,username:e.target.value})}/>
              </div>
            </div>
            <div>
              <label className="form-label">Email</label>
              <input className="input" type="email" placeholder="you@example.com" required
                value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/>
            </div>
            <div>
              <label className="form-label">Password</label>
              <div style={{ position:'relative' }}>
                <input className="input" type={show?'text':'password'}
                  placeholder="Min. 6 characters" required style={{ paddingRight:44 }}
                  value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/>
                <button type="button" onClick={()=>setShow(s=>!s)}
                  style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)',
                    background:'none', border:'none', color:'var(--text3)', cursor:'pointer' }}>
                  {show?<EyeOff size={16}/>:<Eye size={16}/>}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ display:'flex', alignItems:'center', gap:8, padding:'10px 14px',
                background:'var(--red-dim)', border:'1px solid rgba(239,68,68,0.2)',
                borderRadius:'var(--radius)', color:'var(--red)', fontSize:13 }}>
                <AlertCircle size={15}/> {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary" disabled={loading}
              style={{ justifyContent:'center', height:44 }}>
              {loading ? <><div className="spinner"/>&nbsp;Creating…</> : 'Create account'}
            </button>
          </form>
        </div>
        <p style={{ textAlign:'center', marginTop:20, fontSize:14, color:'var(--text3)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color:'var(--accent)', fontWeight:600 }}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}
