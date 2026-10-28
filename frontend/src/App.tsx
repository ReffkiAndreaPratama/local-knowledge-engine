import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Search from './pages/Search'
import Documents from './pages/Documents'
import Assistant from './pages/Assistant'
import Collections from './pages/Collections'
import Jobs from './pages/Jobs'
import Settings from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/search" element={<Search />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/collections" element={<Collections />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
