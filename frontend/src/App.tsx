import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import DocumentsPage from './pages/DocumentsPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ChatPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
