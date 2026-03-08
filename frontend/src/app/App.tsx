import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from '@/context/AppContext'
import { AppLayout } from './AppLayout'
import { SessionsPage } from '@/pages/SessionsPage'
import { ActiveSessionPage } from '@/pages/ActiveSessionPage'
import { SessionDetailPage } from '@/pages/SessionDetailPage'
// Memory & Images pages removed from nav — data is session-scoped (shown in session tabs)
// import { MemoryPage } from '@/pages/MemoryPage'
// import { ImagesPage } from '@/pages/ImagesPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { PasswordGate } from '@/components/PasswordGate'

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <PasswordGate>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<Navigate to="/sessions" replace />} />
              <Route path="/sessions" element={<SessionsPage />} />
              <Route path="/sessions/current" element={<ActiveSessionPage />} />
              <Route path="/sessions/:id" element={<SessionDetailPage />} />
              {/* Memory & Images removed from sidebar — data is session-scoped */}
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </PasswordGate>
      </BrowserRouter>
    </AppProvider>
  )
}
