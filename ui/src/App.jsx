import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Comparison from './pages/Comparison'
import Export from './pages/Export'
import Setting from './pages/Setting'
import Profile from './pages/Profile'

function App() {
  return (
    <Routes>
      {/* Public Authentication Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* Protected Layout Routes */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/history" element={<History />} />
        <Route path="/comparison" element={<Comparison />} />
        <Route path="/export" element={<Export />} />
        <Route path="/setting" element={<Setting />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  )
}

export default App
