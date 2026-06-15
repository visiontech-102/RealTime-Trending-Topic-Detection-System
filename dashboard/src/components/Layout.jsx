import React from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import Navigation from './Navigation'
import { useAuth } from '../contexts/AuthContext'

const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center dark:text-slate-50 bg-slate-50 dark:bg-slate-950 font-bold tracking-widest text-[11px] uppercase text-brand-secondary">Loading System...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen relative bg-slate-50 dark:bg-slate-950 text-slate-950 dark:text-slate-50 font-sans transition-colors duration-300 flex flex-col">
      {/* Top Navbar */}
      <Navigation />
      
      {/* Main Content Pane */}
      <main className="w-full max-w-[1600px] mx-auto p-4 md:p-6 flex-1">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
