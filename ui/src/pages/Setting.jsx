import React, { useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'

const Setting = () => {
  const { isDarkMode, setIsDarkMode } = useTheme();
  const [language, setLanguage] = useState('EN');
  const [autoSave, setAutoSave] = useState(true);
  const [telemetry, setTelemetry] = useState(false);

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex justify-between items-end mb-12">
        <div>
          <h1 className="text-4xl font-extrabold text-slate-950 dark:text-white mb-2 tracking-tight">System Settings</h1>
          <p className="text-slate-500 dark:text-slate-200">Configure environment variables and visual preferences.</p>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">
             LAST CONFIGURED
          </div>
          <div className="flex items-center gap-2 text-[11px] font-bold text-slate-600 uppercase tracking-wider justify-end">
             <div className="w-1.5 h-1.5 rounded-full bg-brand-secondary"></div> 24 OCT 2023 — 14:02 UTC
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-10">
        {/* Left Column configurations */}
        <div className="col-span-8 flex flex-col gap-10">
           
           {/* Language Selection */}
           <div>
             <h2 className="text-[14px] font-bold text-slate-900 dark:text-white mb-4">Language Selection</h2>
             <div className="space-y-3">
               <div 
                 onClick={() => setLanguage('EN')}
                 className={`bg-white dark:bg-slate-900 border shadow-sm rounded-sm p-4 flex items-center justify-between cursor-pointer transition-colors ${language === 'EN' ? 'border-brand-secondary' : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'}`}
               >
                 <div className="flex items-center gap-4">
                   <div className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold text-[10px] px-2 py-1 rounded-sm uppercase tracking-wider">EN</div>
                   <div>
                     <h3 className="text-[13px] font-bold text-slate-900 dark:text-white">English</h3>
                     <p className="text-[11px] text-slate-500 dark:text-slate-200 mt-0.5">Default system interface and primary dataset.</p>
                   </div>
                 </div>
                 <div className={`w-5 h-5 rounded-full border-4 transition-colors ${language === 'EN' ? 'border-white dark:border-slate-800 shadow-[0_0_0_2px_#22c55e] bg-brand-secondary' : 'border border-slate-300 dark:border-slate-700 bg-transparent shadow-none'}`}></div>
               </div>

               <div 
                 onClick={() => setLanguage('SO')}
                 className={`bg-white dark:bg-slate-900 border shadow-sm rounded-sm p-4 flex items-center justify-between cursor-pointer transition-colors ${language === 'SO' ? 'border-brand-secondary' : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-opacity-50'}`}
               >
                 <div className="flex items-center gap-4">
                   <div className="bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-200 font-bold text-[10px] px-2 py-1 rounded-sm uppercase tracking-wider">SO</div>
                   <div>
                     <h3 className="text-[13px] font-bold text-slate-700 dark:text-slate-300">Af-Soomaali</h3>
                     <p className="text-[11px] text-slate-400 dark:text-slate-300 mt-0.5">Secondary dataset and regional trend analysis.</p>
                   </div>
                 </div>
                 <div className={`w-5 h-5 rounded-full transition-colors ${language === 'SO' ? 'border-4 border-white dark:border-slate-800 shadow-[0_0_0_2px_#22c55e] bg-brand-secondary' : 'border border-slate-300 dark:border-slate-700 bg-transparent shadow-none'}`}></div>
               </div>
             </div>
           </div>

           {/* Visual Interface */}
           <div>
              <h2 className="text-[14px] font-bold text-slate-900 dark:text-white mb-4">Visual Interface</h2>
              <div className="grid grid-cols-2 gap-4">
                 <div className="flex flex-col gap-2 opacity-90 cursor-pointer hover:opacity-100 transition-opacity" onClick={() => setIsDarkMode(false)}>
                   <div className={`h-40 bg-slate-50 border-2 rounded-sm p-4 shadow-sm flex flex-col transition-colors ${!isDarkMode ? 'border-brand-secondary' : 'border-transparent'}`}>
                      <div className="w-3/4 h-3 bg-slate-200 rounded-full mb-3"></div>
                      <div className="w-1/2 h-2 bg-slate-200 rounded-full mb-5"></div>
                      <div className="w-full bg-white h-12 shadow-[0_2px_4px_rgba(0,0,0,0.02)] border border-slate-100 rounded-sm mt-auto"></div>
                   </div>
                   <div className="text-center text-[12px] font-bold text-slate-800 dark:text-slate-200">Analytical Light</div>
                 </div>
                 <div className="flex flex-col gap-2 opacity-90 cursor-pointer hover:opacity-100 transition-opacity" onClick={() => setIsDarkMode(true)}>
                   <div className={`h-40 bg-slate-900 border-2 rounded-sm p-4 flex flex-col transition-colors ${isDarkMode ? 'border-brand-secondary' : 'border-transparent'}`}>
                      <div className="w-3/4 h-3 bg-slate-700 rounded-full mb-3"></div>
                      <div className="w-1/2 h-2 bg-slate-700 rounded-full mb-5"></div>
                      <div className="w-full bg-slate-950 h-12 border border-slate-800 rounded-sm mt-auto"></div>
                   </div>
                   <div className="text-center text-[12px] font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors">Monolith Dark</div>
                 </div>
              </div>
           </div>

        </div>

        {/* Right Column sidebar */}
        <div className="col-span-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm p-6 mb-6 transition-colors">
            <h3 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-6">CORE ENGINE STATUS</h3>
            
            <div className="space-y-4 mb-8">
              <div className="flex justify-between items-center text-[12px]">
                <span className="text-slate-500 dark:text-slate-200">Version</span>
                <span className="font-bold text-slate-900 dark:text-white">4.8.2-stable</span>
              </div>
              <div className="flex justify-between items-center text-[12px]">
                <span className="text-slate-500 dark:text-slate-200">API<br/>Endpoint</span>
                <div className="flex items-center gap-2">
                   <span className="bg-brand-secondary/50 dark:bg-brand-secondary/30 text-brand-secondary dark:text-brand-secondary text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded-sm tracking-wider">ACTIVE</span>
                   <span className="font-bold text-slate-900 dark:text-white">v2.visiontech.ai</span>
                </div>
              </div>
              <div className="flex justify-between items-center text-[12px]">
                <span className="text-slate-500 dark:text-slate-200">Uptime</span>
                <span className="font-bold text-slate-900 dark:text-white">99.98%</span>
              </div>
            </div>

            <h3 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-4">DATA PERSISTENCE</h3>
            <div className="space-y-4 mb-8">
              <div className="flex justify-between items-center text-[12px]">
                <span className="text-slate-700 dark:text-slate-300">Auto-save settings</span>
                <div onClick={() => setAutoSave(!autoSave)} className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${autoSave ? 'bg-brand-secondary' : 'bg-slate-200 dark:bg-slate-700'}`}>
                  <div className={`w-4 h-4 bg-white dark:bg-slate-100 rounded-full absolute top-0.5 shadow-sm transition-all ${autoSave ? 'right-0.5' : 'left-0.5'}`}></div>
                </div>
              </div>
              <div className="flex justify-between items-center text-[12px] opacity-60">
                <span className="text-slate-700 dark:text-slate-300">Telemetry sharing</span>
                <div onClick={() => setTelemetry(!telemetry)} className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${telemetry ? 'bg-brand-secondary' : 'bg-slate-200 dark:bg-slate-700'}`}>
                  <div className={`w-4 h-4 bg-white dark:bg-slate-100 rounded-full absolute top-0.5 shadow-sm transition-all ${telemetry ? 'right-0.5' : 'left-0.5'}`}></div>
                </div>
              </div>
            </div>

            <button className="w-full bg-slate-950 dark:bg-slate-800 text-white text-[10px] font-extrabold uppercase tracking-widest py-3 rounded-sm flex items-center justify-center gap-2 hover:bg-slate-800 dark:hover:bg-slate-700 transition-colors">
              REBOOT ENGINE <span>&#x21BA;</span>
            </button>
          </div>

          <div className="bg-slate-100/50 dark:bg-slate-800/30 border border-slate-200 dark:border-slate-800 shadow-sm rounded-sm p-6 text-sm transition-colors">
             <div className="w-6 h-6 rounded border border-brand-secondary flex items-center justify-center text-brand-secondary mb-3">
               <span className="text-[10px]">&#10003;</span>
             </div>
             <h4 className="font-bold text-slate-900 dark:text-slate-100 mb-1 leading-tight">Enterprise Grade Security</h4>
             <p className="text-xs text-slate-500 dark:text-slate-200 leading-relaxed">
               All configuration changes are logged and encrypted using AES-256 standards for institutional transparency.
             </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Setting
