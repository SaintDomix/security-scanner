import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { User, Key, Bell, Shield, CheckCircle } from 'lucide-react'

export default function Settings() {
  const { user } = useAuth()
  const [saved, setSaved] = useState(false)

  const showSaved = () => { setSaved(true); setTimeout(()=>setSaved(false), 2500) }

  return (
    <div className="animate-in">
      <div style={{ marginBottom:28 }}>
        <h1 style={{ fontSize:22, fontWeight:700, marginBottom:4 }}>Settings</h1>
        <p style={{ color:'var(--text3)', fontSize:14 }}>Account and preferences</p>
      </div>

      {saved && (
        <div style={{ marginBottom:16, display:'flex', alignItems:'center', gap:8,
          padding:'10px 16px', background:'var(--green-dim)',
          border:'1px solid rgba(16,185,129,0.3)', borderRadius:'var(--radius)',
          color:'var(--green)', fontSize:13 }}>
          <CheckCircle size={15}/> Settings saved
        </div>
      )}

      <div style={{ display:'flex', flexDirection:'column', gap:20, maxWidth:640 }}>
        {/* Profile */}
        <div className="card" style={{ padding:24 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:20 }}>
            <User size={18} style={{ color:'var(--accent)' }}/>
            <h2 style={{ fontSize:15, fontWeight:600 }}>Profile</h2>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
            <div className="grid-2">
              <div>
                <label className="form-label">Username</label>
                <input className="input" defaultValue={user?.username} readOnly style={{ opacity:0.6 }}/>
              </div>
              <div>
                <label className="form-label">Full Name</label>
                <input className="input" defaultValue={user?.full_name || ''} placeholder="Your name"/>
              </div>
            </div>
            <div>
              <label className="form-label">Email</label>
              <input className="input" defaultValue={user?.email} readOnly style={{ opacity:0.6 }}/>
            </div>
            <button className="btn btn-primary btn-sm" style={{ alignSelf:'flex-start' }}
              onClick={showSaved}>
              Save changes
            </button>
          </div>
        </div>

        {/* Security */}
        <div className="card" style={{ padding:24 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:20 }}>
            <Key size={18} style={{ color:'var(--orange)' }}/>
            <h2 style={{ fontSize:15, fontWeight:600 }}>Security</h2>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
            <div>
              <label className="form-label">Current password</label>
              <input className="input" type="password" placeholder="••••••••"/>
            </div>
            <div className="grid-2">
              <div>
                <label className="form-label">New password</label>
                <input className="input" type="password" placeholder="••••••••"/>
              </div>
              <div>
                <label className="form-label">Confirm password</label>
                <input className="input" type="password" placeholder="••••••••"/>
              </div>
            </div>
            <button className="btn btn-ghost btn-sm" style={{ alignSelf:'flex-start' }}
              onClick={showSaved}>
              Change password
            </button>
          </div>
        </div>

        {/* Subscription info */}
        <div className="card" style={{ padding:24 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
            <Shield size={18} style={{ color:'var(--purple)' }}/>
            <h2 style={{ fontSize:15, fontWeight:600 }}>Subscription</h2>
          </div>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
            padding:'12px 16px', background:'var(--bg2)', borderRadius:'var(--radius)',
            border:'1px solid var(--border)' }}>
            <div>
              <div style={{ fontWeight:600, textTransform:'capitalize' }}>
                {user?.subscription_tier} Plan
              </div>
              <div style={{ fontSize:12, color:'var(--text3)' }}>
                {user?.scans_today} scans used today
              </div>
            </div>
            <a href="/pricing" className="btn btn-primary btn-sm">Manage plan</a>
          </div>
        </div>

        {/* Notifications */}
        <div className="card" style={{ padding:24 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
            <Bell size={18} style={{ color:'var(--cyan)' }}/>
            <h2 style={{ fontSize:15, fontWeight:600 }}>Notifications</h2>
          </div>
          {[
            'Email me when a scan completes',
            'Email me on critical findings',
            'Weekly security digest',
          ].map(label => (
            <label key={label} style={{ display:'flex', justifyContent:'space-between',
              alignItems:'center', padding:'10px 0', borderBottom:'1px solid var(--border)',
              cursor:'pointer' }}>
              <span style={{ fontSize:13 }}>{label}</span>
              <input type="checkbox" defaultChecked style={{ accentColor:'var(--accent)', width:16, height:16 }}/>
            </label>
          ))}
          <button className="btn btn-primary btn-sm" style={{ marginTop:16 }} onClick={showSaved}>
            Save preferences
          </button>
        </div>

        {/* Danger zone */}
        <div className="card" style={{ padding:24, borderColor:'rgba(239,68,68,0.2)' }}>
          <h2 style={{ fontSize:15, fontWeight:600, color:'var(--red)', marginBottom:12 }}>Danger zone</h2>
          <div style={{ fontSize:13, color:'var(--text3)', marginBottom:14 }}>
            Deleting your account is permanent and removes all scan history.
          </div>
          <button className="btn btn-danger btn-sm">Delete account</button>
        </div>
      </div>
    </div>
  )
}
