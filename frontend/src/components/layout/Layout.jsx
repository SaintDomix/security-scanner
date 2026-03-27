import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  Shield, LayoutDashboard, Search, Globe, History,
  CreditCard, Settings, LogOut, ChevronRight, Zap, Menu, X
} from 'lucide-react'
import { useState } from 'react'

const nav = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/scan/sast',  icon: Search,          label: 'SAST / Secrets' },
  { to: '/scan/dast',  icon: Globe,           label: 'DAST Scan',    pro: true },
  { to: '/history',    icon: History,         label: 'Scan History' },
  { to: '/pricing',    icon: CreditCard,      label: 'Pricing' },
  { to: '/settings',   icon: Settings,        label: 'Settings' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const tierColor = { free: '#64748B', pro: '#3B82F6', enterprise: '#8B5CF6' }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Mobile overlay */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)', zIndex:40 }}
        />
      )}

      {/* Sidebar */}
      <aside style={{
        width: 240, background: 'var(--bg2)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        position: 'fixed', top: 0, bottom: 0, left: open ? 0 : -240,
        zIndex: 50, transition: 'left 0.25s ease',
        '@media(min-width:768px)': { left: 0 }
      }}
      className="sidebar">
        {/* Logo */}
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <div style={{
              width:36, height:36, borderRadius:8,
              background: 'linear-gradient(135deg,#3B82F6,#1D4ED8)',
              display:'flex', alignItems:'center', justifyContent:'center'
            }}>
              <Shield size={20} color="#fff" />
            </div>
            <div>
              <div style={{ fontSize:15, fontWeight:700, color:'var(--text)' }}>SecureScanner</div>
              <div style={{ fontSize:11, color:'var(--text3)', fontFamily:'var(--font-mono)' }}>v2.0</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex:1, padding:'12px 8px', display:'flex', flexDirection:'column', gap:2 }}>
          {nav.map(({ to, icon: Icon, label, pro }) => (
            <NavLink key={to} to={to} onClick={() => setOpen(false)} style={({ isActive }) => ({
              display:'flex', alignItems:'center', gap:10, padding:'9px 12px',
              borderRadius:'var(--radius)', fontSize:14, fontWeight:500,
              textDecoration:'none', transition:'all 0.15s',
              color: isActive ? 'var(--text)' : 'var(--text3)',
              background: isActive ? 'var(--surface2)' : 'transparent',
            })}>
              {({ isActive }) => (
                <>
                  <Icon size={17} style={{ color: isActive ? 'var(--accent)' : 'currentColor' }} />
                  <span style={{ flex:1 }}>{label}</span>
                  {pro && user?.subscription_tier === 'free' && (
                    <span style={{ fontSize:10, fontWeight:700, color:'var(--accent)', background:'var(--accent-glow)', padding:'1px 5px', borderRadius:3 }}>PRO</span>
                  )}
                  {isActive && <ChevronRight size={14} style={{ opacity:0.4 }} />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div style={{ padding:'12px 16px', borderTop:'1px solid var(--border)' }}>
          <div style={{ marginBottom:8 }}>
            <div style={{ fontSize:13, fontWeight:600, color:'var(--text)', marginBottom:2 }}>
              {user?.username}
            </div>
            <div style={{ fontSize:11, color:'var(--text3)', marginBottom:6 }}>{user?.email}</div>
            <span style={{
              fontSize:11, fontWeight:700, padding:'2px 8px', borderRadius:4,
              color: tierColor[user?.subscription_tier] || '#64748B',
              background: `${tierColor[user?.subscription_tier]}22`,
              textTransform:'uppercase', letterSpacing:'0.05em'
            }}>
              {user?.subscription_tier} plan
            </span>
          </div>
          <button onClick={() => { logout(); navigate('/login') }}
            className="btn btn-ghost btn-sm" style={{ width:'100%', justifyContent:'center' }}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div style={{ flex:1, marginLeft:240, display:'flex', flexDirection:'column', minHeight:'100vh' }}
           className="main-content">
        {/* Top bar */}
        <header style={{
          height:56, background:'var(--bg2)', borderBottom:'1px solid var(--border)',
          display:'flex', alignItems:'center', padding:'0 24px', gap:12,
          position:'sticky', top:0, zIndex:30
        }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setOpen(o => !o)}
            style={{ padding:'6px', display:'flex' }}>
            {open ? <X size={18}/> : <Menu size={18}/>}
          </button>
          <div style={{ flex:1 }} />
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <Zap size={14} style={{ color:'var(--accent)' }} />
            <span style={{ fontSize:13, color:'var(--text2)' }}>
              {user?.scans_today} scans today
            </span>
          </div>
        </header>

        <main style={{ flex:1, padding:'32px 32px', maxWidth:1200, width:'100%', margin:'0 auto' }}>
          <Outlet />
        </main>
      </div>

      <style>{`
        @media (min-width: 769px) {
          .sidebar { left: 0 !important; }
          .main-content { margin-left: 240px !important; }
        }
        @media (max-width: 768px) {
          .main-content { margin-left: 0 !important; }
        }
      `}</style>
    </div>
  )
}
