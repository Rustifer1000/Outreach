import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import ContactDetail from './pages/ContactDetail'
import Mentions from './pages/Mentions'
import Rotation from './pages/Rotation'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/mentions" element={<Mentions />} />
          <Route path="/rotation" element={<Rotation />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/contacts/:id" element={<ContactDetail />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
