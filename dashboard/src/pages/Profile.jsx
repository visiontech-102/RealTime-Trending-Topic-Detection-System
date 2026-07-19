import React from 'react'
import { LogOut } from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const Profile = () => {
  const { isDarkMode, setIsDarkMode } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="mb-10">
        <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white tracking-tight">{t('profile') || 'User Profile'}</h1>
      </div>

      {/* Profile Card — full width */}
      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-2xl p-8 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-xl bg-brand-primary/10 dark:bg-brand-primary/20 flex items-center justify-center shrink-0">
              <span className="text-2xl font-extrabold select-none" style={{ color: '#1E3A8A' }}>
                {(user?.name || user?.username || 'U').substring(0, 2).toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-brand-primary dark:text-white capitalize leading-tight">
                {user?.name || user?.username || 'User'}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{user?.email || ''}</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/setting')}
            className="self-start sm:self-auto shrink-0 bg-brand-primary hover:bg-brand-secondary text-white font-bold text-xs uppercase tracking-widest px-5 py-2.5 rounded-lg transition-colors shadow-sm"
          >
            Go to Settings
          </button>
        </div>
      </div>

      {/* Preferences — 2 equal columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Language */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-6 transition-colors">
          <h3 className="text-[11px] font-bold text-brand-primary dark:text-slate-200 uppercase tracking-wider mb-4">Language Preference</h3>
          <div className="space-y-2">
            {[
              { val: 'en', label: 'English / Somali (EN/SO)' },
              { val: 'so', label: 'Somali / English (SO/EN)' },
            ].map(({ val, label }) => (
              <div
                key={val}
                onClick={() => setLanguage(val)}
                className={`cursor-pointer font-bold text-xs p-3 rounded-lg flex justify-between items-center transition-colors ${language === val ? 'bg-brand-primary text-white' : 'bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-brand-primary/40'}`}
              >
                {label}
                {language === val && <span className="text-white text-[10px]">&#10003;</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Theme */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-6 transition-colors">
          <h3 className="text-[11px] font-bold text-brand-primary dark:text-slate-200 uppercase tracking-wider mb-4">Interface Theme</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Light', icon: '☀', active: !isDarkMode, onClick: () => setIsDarkMode(false) },
              { label: 'Dark',  icon: '🌙', active: isDarkMode,  onClick: () => setIsDarkMode(true)  },
            ].map(({ label, icon, active, onClick }) => (
              <div
                key={label}
                onClick={onClick}
                className={`cursor-pointer font-bold text-[11px] uppercase tracking-wider py-5 rounded-lg flex flex-col items-center gap-2 transition-colors ${active ? 'bg-brand-primary text-white' : 'bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 text-slate-500 dark:text-slate-300 hover:border-brand-primary/40'}`}
              >
                <span className="text-xl">{icon}</span>
                {label}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sign Out — full width */}
      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-6 transition-colors flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Sign out of your account</p>
          <p className="text-xs text-slate-400 mt-0.5">You will be redirected to the login page.</p>
        </div>
        <button
          onClick={handleLogout}
          className="w-full sm:w-auto shrink-0 flex items-center justify-center gap-2 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 font-bold text-[11px] uppercase tracking-wider px-8 py-3 rounded-lg transition-colors"
        >
          <LogOut size={15} />
          {t('logout') || 'Sign Out'}
        </button>
      </div>
    </div>
  )
}

export default Profile
