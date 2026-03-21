import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import LoginGuard from './LoginGuard'
import App from './App'
import AdminLayout from './admin/AdminLayout'
import Dashboard from './admin/Dashboard'
import Tuning from './admin/Tuning'
import History from './admin/History'
import DataBrowser from './admin/DataBrowser'
import Tests from './admin/Tests'
import Logs from './admin/Logs'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LoginGuard>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="tuning" element={<Tuning />} />
            <Route path="tests" element={<Tests />} />
            <Route path="data" element={<DataBrowser />} />
            <Route path="history" element={<History />} />
            <Route path="logs" element={<Logs />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LoginGuard>
  </StrictMode>,
)
