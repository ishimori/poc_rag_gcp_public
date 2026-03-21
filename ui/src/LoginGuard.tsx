import { useState, type ReactNode, type FormEvent } from 'react'

const AUTH_KEY = 'rag-poc-auth'
const VALID_ID = 'orange'
const VALID_PW = 'one'

export default function LoginGuard({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(
    () => sessionStorage.getItem(AUTH_KEY) === 'true'
  )
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  if (authenticated) return <>{children}</>

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (userId === VALID_ID && password === VALID_PW) {
      sessionStorage.setItem(AUTH_KEY, 'true')
      setAuthenticated(true)
    } else {
      setError('IDまたはパスワードが正しくありません')
    }
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      background: '#f8f9fa',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: '#fff', padding: '40px', borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)', width: '340px',
      }}>
        <h2 style={{ margin: '0 0 24px', fontSize: '1.25rem', textAlign: 'center' }}>
          RAG PoC ログイン
        </h2>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem', color: '#555' }}>ID</label>
          <input
            type="text"
            value={userId}
            onChange={e => setUserId(e.target.value)}
            autoComplete="username"
            style={{
              width: '100%', padding: '10px 12px', border: '1px solid #ddd',
              borderRadius: '4px', fontSize: '1rem',
            }}
          />
        </div>
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.85rem', color: '#555' }}>パスワード</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="current-password"
            style={{
              width: '100%', padding: '10px 12px', border: '1px solid #ddd',
              borderRadius: '4px', fontSize: '1rem',
            }}
          />
        </div>
        {error && (
          <p style={{ color: '#d93025', fontSize: '0.85rem', margin: '0 0 16px', textAlign: 'center' }}>
            {error}
          </p>
        )}
        <button type="submit" style={{
          width: '100%', padding: '10px', background: '#1a73e8', color: '#fff',
          border: 'none', borderRadius: '4px', fontSize: '1rem', cursor: 'pointer',
        }}>
          ログイン
        </button>
      </form>
    </div>
  )
}
