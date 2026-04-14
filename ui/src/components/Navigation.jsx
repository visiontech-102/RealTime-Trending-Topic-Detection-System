import React from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { Globe, Moon, Sun, User, LogOut } from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useAuth } from '../contexts/AuthContext'

const Navigation = () => {
  const { isDarkMode, toggleTheme } = useTheme();
  const { toggleLanguage, t, language } = useLanguage();
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const navLinks = [
    { name: 'dashboard', path: '/dashboard' },
    { name: 'history', path: '/history' },
    { name: 'comparison', path: '/comparison' },
    { name: 'export', path: '/export' },
    { name: 'settings', path: '/setting' },
  ]

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-brand-primary border-b border-brand-primary/90 px-4 md:px-8 py-3 lg:py-4 flex flex-col md:flex-row items-center justify-between sticky top-0 z-50 transition-colors duration-300 gap-4 md:gap-0 w-full overflow-hidden">
      <div className="flex items-center gap-4 lg:gap-8 overflow-hidden w-full md:w-auto max-w-full">
        <Link to="/" className="flex flex-col shrink-0">
          <span className="text-lg lg:text-xl font-bold tracking-tight text-white leading-none pb-0.5">Vision Tech</span>
          <span className="text-[8px] lg:text-[9px] text-brand-secondary font-bold uppercase tracking-widest leading-none">Topic Detection</span>
        </Link>
        <nav className="flex items-center gap-4 lg:gap-6 overflow-x-auto w-full flex-1 pb-1 pt-1 scroll-smooth">
          {navLinks.map((link) => (
            <NavLink 
              key={link.name} 
              to={link.path}
              className={({ isActive }) => 
                `text-[10px] lg:text-xs font-bold uppercase tracking-wider transition-colors pb-1 border-b-2 whitespace-nowrap shrink-0 ${
                  isActive
                  ? 'text-brand-secondary border-brand-secondary' 
                  : 'text-slate-300 hover:text-brand-secondary border-transparent'
                }`
              }
            >
              {t(link.name)}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4 lg:gap-5 text-slate-300 shrink-0 self-start md:self-auto w-full md:w-auto justify-between border-t border-brand-primary/80 md:border-t-0 pt-3 md:pt-0">
        <button onClick={toggleLanguage} className="hover:text-white transition-colors flex items-center gap-1 text-sm font-medium uppercase">
          <Globe size={18} />
          {language === 'en' ? 'SO' : 'EN'}
        </button>
        <button onClick={toggleTheme} className="hover:text-brand-secondary transition-colors">
          {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        <Link to="/profile" className="flex items-center gap-2 px-3 py-1.5 border border-brand-secondary/30 rounded-xl hover:bg-white/10 transition-colors text-white">
          <span className="text-xs font-bold uppercase tracking-wider">{t('profile')}</span>
          <div className="w-5 h-5 bg-brand-secondary text-white rounded-full flex items-center justify-center">
            <User size={12} fill="currentColor" />
          </div>
        </Link>
        <button onClick={handleLogout} className="hover:text-red-400 transition-colors" title={t('logout')}>
          <LogOut size={20} />
        </button>
      </div>
    </header>
  )
}

export default Navigation
