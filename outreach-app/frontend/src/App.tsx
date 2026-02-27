import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Contacts from './pages/Contacts'
import ContactDetail from './pages/ContactDetail'
import NamesFile from './pages/NamesFile'
import RelationshipMap from './pages/RelationshipMap'
import Rotation from './pages/Rotation'
import Digest from './pages/Digest'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/contacts/:id" element={<ContactDetail />} />
          <Route path="/rotation" element={<Rotation />} />
          <Route path="/map" element={<RelationshipMap />} />
          <Route path="/digest" element={<Digest />} />
          <Route path="/names-file" element={<NamesFile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
