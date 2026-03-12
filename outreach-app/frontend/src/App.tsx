import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import ContactDetail from './pages/ContactDetail'
import Mentions from './pages/Mentions'
import Rotation from './pages/Rotation'
import Outreach from './pages/Outreach'
import Notes from './pages/Notes'
import Enrichment from './pages/Enrichment'
import Analytics from './pages/Analytics'
import Network from './pages/Network'
import Templates from './pages/Templates'
import Digest from './pages/Digest'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/mentions" element={<Mentions />} />
          <Route path="/rotation" element={<Rotation />} />
          <Route path="/outreach" element={<Outreach />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/contacts/:id" element={<ContactDetail />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/enrichment" element={<Enrichment />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/network" element={<Network />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/digest" element={<Digest />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
