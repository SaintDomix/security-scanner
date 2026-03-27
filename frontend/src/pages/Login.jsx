import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await login(form.email, form.password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight:'100vh', background:'var(--bg)',
      display:'flex', alignItems:'center', justifyContent:'center',
      padding:24
    }}>
      {/* Background grid */}
      <div style={{
        position:'fixed', inset:0, opacity:0.03,
        backgroundImage:'linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px)',
        backgroundSize:'40px 40px', pointerEvents:'none'
      }}/>

      <div className="animate-in" style={{ width:'100%', maxWidth:420 }}>
        {/* Logo */}
        <div style={{ textAlign:'center', marginBottom:32 }}>
          <div style={{
            width:56, height:56, borderRadius:14, margin:'0 auto 16px',
            background:'linear-gradient(135deg,#3B82F6,#1D4ED8)',
            display:'flex', alignItems:'center', justifyContent:'center',
            boxShadow:'0 8px 32px rgba(59,130,246,0.4)'
          }}>
            <Shield size={28} color="#fff" />
          </div>
          <h1 style={{ fontSize:26, fontWeight:700, color:'var(--text)', marginBottom:6 }}>
            SecureScanner
          </h1>
          <p style={{ color:'var(--text3)', fontSize:14 }}>Sign in to your account</p>
        </div>

        <div className="card" style={{ padding:32 }}>
          <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap:20 }}>
            <div>
              <label className="form-label">Email</label>
              <input className="input" type="email" placeholder="you@example.com"
                value={form.email} onChange={e => setForm({...form, email:e.target.value})} required />
            </div>
            <div>
              <label className="form-label">Password</label>
              <div style={{ position:'relative' }}>
                <input className="input" type={show ? 'text':'password'}
                  placeholder="••••••••" style={{ paddingRight:44 }}
                  value={form.password} onChange={e => setForm({...form, password:e.target.value})} required />
                <button type="button" onClick={() => setShow(s=>!s)}
                  style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)',
                    background:'none', border:'none', color:'var(--text3)', cursor:'pointer', padding:0 }}>
                  {show ? <EyeOff size={16}/> : <Eye size={16}/>}
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
              {loading ? <><div className="spinner"/>&nbsp;Signing in…</> : 'Sign in'}
            </button>
          </form>
        </div>

        <p style={{ textAlign:'center', marginTop:20, fontSize:14, color:'var(--text3)' }}>
          No account?{' '}
          <Link to="/register" style={{ color:'var(--accent)', fontWeight:600 }}>Create one free</Link>
        </p>
      </div>
    </div>
  )
}
