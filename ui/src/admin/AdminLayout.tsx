import { NavLink, Outlet } from 'react-router-dom'
import './admin.css'

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/tuning', label: 'Tuning' },
  { to: '/admin/tests', label: 'Tests' },
  { to: '/admin/data', label: 'Data' },
  { to: '/admin/history', label: 'History' },
  { to: '/admin/logs', label: 'Logs' },
]

export default function AdminLayout() {
  return (
    <div className="admin-layout">
      <nav className="admin-nav">
        <div className="admin-nav-title">
          <a href="/" className="admin-back-link">← Chat</a>
          <h2>Admin</h2>
        </div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  )
}
