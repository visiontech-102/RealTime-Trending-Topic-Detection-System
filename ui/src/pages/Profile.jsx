import React from 'react'
import { User, LogOut } from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'

const Profile = () => {
  const { isDarkMode, setIsDarkMode } = useTheme()
  const { language, setLanguage, t } = useLanguage()

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h2 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-2">SYSTEM ENTITY</h2>
          <h1 className="text-4xl font-extrabold text-slate-950 dark:text-white tracking-tight">{t('profile') || 'User Profile'}</h1>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 text-[10px] font-extrabold text-brand-secondary uppercase tracking-widest mb-1 justify-end">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-secondary"></div>
            LIVE STATUS: AUTHORIZED
          </div>
          <div className="text-[10px] text-slate-400 uppercase">Last accessed: {(new Date()).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })} · {(new Date()).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })} UTC</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
        {/* Left Column Profile Info */}
        <div className="col-span-1 lg:col-span-8">
          <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm p-8 pb-10 transition-colors">
            <div className="flex items-center gap-6 mb-12">
              <div className="w-28 h-28 bg-slate-900 dark:bg-slate-800 rounded-sm relative overflow-hidden flex items-center justify-center">
                 {/* Representing the avatar drawing visually simply */}
                 <User size={64} className="text-slate-700 dark:text-slate-300" />
                 <div className="absolute bottom-2 text-[8px] text-slate-500 font-bold tracking-widest">CURATOR</div>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-950 dark:text-white">Adrian Thorne</h2>
                <div className="text-sm font-medium text-slate-500 dark:text-slate-200 mb-3">adrian.thorne@visiontech.io</div>
                <span className="bg-brand-secondary/20 text-brand-secondary text-[10px] font-extrabold px-3 py-1 rounded-sm tracking-wider">PRIMARY CURATOR</span>
              </div>
            </div>

            <div className="border-t border-slate-100 dark:border-slate-800 pt-6 lg:pt-8 grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-8 mb-10">
              <div>
                <h3 className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-widest mb-1">ACCESS LEVEL</h3>
                <div className="text-slate-800 dark:text-slate-200 font-medium">Full Administrative Access</div>
              </div>
              <div>
                <h3 className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-widest mb-1">DATE JOINED</h3>
                <div className="text-slate-800 dark:text-slate-200 font-medium">January 2023</div>
              </div>
            </div>

            <div className="flex gap-4">
              <button className="bg-slate-950 dark:bg-slate-800 text-white font-bold text-[11px] uppercase tracking-wider px-6 py-3 rounded-sm hover:-translate-y-0.5 transition-transform">
                UPDATE METADATA
              </button>
              <button className="bg-slate-100 dark:bg-slate-800/50 text-slate-600 dark:text-slate-300 font-bold text-[11px] uppercase tracking-wider px-6 py-3 rounded-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">
                SECURITY LOG
              </button>
            </div>
          </div>
        </div>

        {/* Right Column Preferences */}
        <div className="col-span-1 lg:col-span-4 space-y-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm p-6 transition-colors">
            <div className="flex items-center gap-2 text-[11px] font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-4">
               <span className="text-brand-secondary">&#25106;</span> LANGUAGE PREFERENCE
            </div>
            <div className="space-y-2">
              <div 
                onClick={() => setLanguage('en')}
                className={`cursor-pointer font-bold text-xs p-3 rounded-sm flex justify-between items-center shadow-sm transition-colors ${language === 'en' ? 'bg-brand-secondary text-slate-950' : 'bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 text-slate-500 dark:text-slate-200'}`}
              >
                ENGLISH / SOMALI (EN/SO)
                {language === 'en' && (
                  <div className="w-3 h-3 bg-slate-950 rounded-full flex items-center justify-center">
                    <span className="text-brand-secondary text-[8px]">&#10003;</span>
                  </div>
                )}
              </div>
              <div 
                onClick={() => setLanguage('so')}
                className={`cursor-pointer font-bold text-xs p-3 rounded-sm flex justify-between items-center shadow-sm transition-colors ${language === 'so' ? 'bg-brand-secondary text-slate-950' : 'bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 text-slate-500 dark:text-slate-200'}`}
              >
                SOMALI / ENGLISH (SO/EN)
                {language === 'so' && (
                  <div className="w-3 h-3 bg-slate-950 rounded-full flex items-center justify-center">
                    <span className="text-brand-secondary text-[8px]">&#10003;</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm p-6 transition-colors">
             <div className="flex items-center gap-2 text-[11px] font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-4">
               <span className="text-brand-secondary">&#9728;</span> INTERFACE THEME
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div 
                onClick={() => setIsDarkMode(false)}
                className={`font-bold text-[10px] uppercase tracking-wider py-4 rounded-sm flex flex-col items-center gap-2 shadow-sm cursor-pointer transition-colors ${!isDarkMode ? 'bg-brand-secondary text-slate-950' : 'bg-white dark:bg-transparent border border-slate-100 dark:border-slate-700 text-slate-400 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
              >
                 <span className="text-lg">&#9728;</span>
                 LIGHT
              </div>
              <div 
                onClick={() => setIsDarkMode(true)}
                className={`font-bold text-[10px] uppercase tracking-wider py-4 rounded-sm flex flex-col items-center gap-2 shadow-sm cursor-pointer transition-colors ${isDarkMode ? 'bg-brand-secondary text-slate-950' : 'bg-white dark:bg-transparent border border-slate-100 dark:border-slate-700 text-slate-400 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
              >
                 <span className="text-lg">&#9789;</span>
                 DARK
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default Profile
