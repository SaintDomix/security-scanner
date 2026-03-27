import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { usersAPI } from '../utils/api'
import { Check, Zap, Shield, Crown } from 'lucide-react'

const PLANS = [
  {
    id: 'free', name: 'Free', price: '$0', period: 'forever', icon: Shield, color: '#64748B',
    features: ['3 scans per day', 'SAST scan (Semgrep + Bearer)', 'Secret detection (Gitleaks)', 'PDF reports', 'Scan history'],
    missing: ['DAST live scanning', 'GitHub API validation', 'Priority support'],
  },
  {
    id: 'pro', name: 'Pro', price: '$19', period: '/month', icon: Zap, color: '#3B82F6', popular: true,
    features: ['50 scans per day', 'Everything in Free', 'DAST live scanning', 'Full GitHub repo validation', 'OWASP ZAP integration', 'Priority support'],
    missing: ['Team accounts'],
  },
  {
    id: 'enterprise', name: 'Enterprise', price: '$79', period: '/month', icon: Crown, color: '#8B5CF6',
    features: ['Unlimited scans', 'Everything in Pro', 'Team accounts (up to 10)', 'API access', 'SSO / SAML', 'Dedicated support', 'Custom rules'],
    missing: [],
  },
]

export default function Pricing() {
  const { user, refreshUser } = useAuth()
  const [loading, setLoading] = useState('')
  const [success, setSuccess] = useState('')

  const upgrade = async (tier) => {
    if (tier === user?.subscription_tier) return
    setLoading(tier); setSuccess('')
    try {
      await usersAPI.upgrade(tier)
      await refreshUser()
      setSuccess(`Upgraded to ${tier}!`)
    } catch {}
    finally { setLoading('') }
  }

  return (
    <div className="animate-in">
      <div style={{ textAlign:'center', marginBottom:40 }}>
        <h1 style={{ fontSize:26, fontWeight:700, marginBottom:8 }}>Simple pricing</h1>
        <p style={{ color:'var(--text3)', fontSize:15 }}>
          Start free. Upgrade when you need more power.
        </p>
        {success && (
          <div style={{ marginTop:16, display:'inline-block', padding:'8px 20px',
            background:'var(--green-dim)', border:'1px solid rgba(16,185,129,0.3)',
            borderRadius:'var(--radius)', color:'var(--green)', fontWeight:600 }}>
            ✓ {success}
          </div>
        )}
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:20, maxWidth:900, margin:'0 auto' }}
           className="plans-grid">
        {PLANS.map(plan => {
          const Icon = plan.icon
          const isCurrent = user?.subscription_tier === plan.id
          const isLoading = loading === plan.id
          return (
            <div key={plan.id} className="card" style={{
              padding:28, position:'relative', overflow:'hidden',
              border: plan.popular ? `2px solid ${plan.color}` : undefined,
              background: isCurrent ? `${plan.color}08` : undefined,
            }}>
              {plan.popular && (
                <div style={{ position:'absolute', top:16, right:16,
                  fontSize:11, fontWeight:700, color:plan.color,
                  background:`${plan.color}22`, padding:'2px 8px', borderRadius:4 }}>
                  POPULAR
                </div>
              )}
              {isCurrent && (
                <div style={{ position:'absolute', top:16, right:16,
                  fontSize:11, fontWeight:700, color:'var(--green)',
                  background:'var(--green-dim)', padding:'2px 8px', borderRadius:4 }}>
                  CURRENT
                </div>
              )}

              <div style={{ width:44, height:44, borderRadius:12, background:`${plan.color}22`,
                display:'flex', alignItems:'center', justifyContent:'center', marginBottom:16 }}>
                <Icon size={22} style={{ color:plan.color }}/>
              </div>

              <div style={{ fontSize:18, fontWeight:700, marginBottom:4 }}>{plan.name}</div>
              <div style={{ marginBottom:20 }}>
                <span style={{ fontSize:32, fontWeight:800, color:plan.color }}>{plan.price}</span>
                <span style={{ fontSize:14, color:'var(--text3)' }}>{plan.period}</span>
              </div>

              <div style={{ borderTop:'1px solid var(--border)', paddingTop:20, marginBottom:20 }}>
                {plan.features.map(f=>(
                  <div key={f} style={{ display:'flex', gap:8, marginBottom:8, fontSize:13 }}>
                    <Check size={15} style={{ color:'var(--green)', flexShrink:0, marginTop:1 }}/> {f}
                  </div>
                ))}
                {plan.missing.map(f=>(
                  <div key={f} style={{ display:'flex', gap:8, marginBottom:8, fontSize:13, opacity:0.4 }}>
                    <span style={{ width:15, height:15, flexShrink:0, textAlign:'center', lineHeight:'15px', fontSize:10 }}>✗</span>
                    {f}
                  </div>
                ))}
              </div>

              <button
                className="btn"
                style={{ width:'100%', justifyContent:'center',
                  background: isCurrent ? 'var(--surface2)' : plan.color,
                  color: isCurrent ? 'var(--text2)' : '#fff',
                  cursor: isCurrent ? 'default' : 'pointer' }}
                disabled={isCurrent || !!loading}
                onClick={() => upgrade(plan.id)}>
                {isLoading ? <><div className="spinner" style={{ borderTopColor:'#fff' }}/>&nbsp;Upgrading…</>
                  : isCurrent ? 'Current plan'
                  : plan.id === 'free' ? 'Downgrade'
                  : `Upgrade to ${plan.name}`}
              </button>
            </div>
          )
        })}
      </div>

      <div style={{ marginTop:40, textAlign:'center', color:'var(--text3)', fontSize:13 }}>
        <p>This is a demo — payments are simulated. In production, integrate Stripe Checkout.</p>
      </div>

      <style>{`
        @media (max-width: 768px) { .plans-grid { grid-template-columns: 1fr !important; } }
      `}</style>
    </div>
  )
}
