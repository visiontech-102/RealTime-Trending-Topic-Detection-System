import React from 'react'
import { Eye } from 'lucide-react'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { useLanguage } from '../contexts/LanguageContext'

const MOCK_DATA = {
  '24 HOURS': {
    total: '1,284',
    avg: '78.4',
    top: 'HARGEISA, SO',
    trends: [
      { topic: '#RenewableEnergyAfrica', type: 'Politics & Tech', date: 'Oct 24, 2023 · 14:32', lang: 'ENGLISH', score: 92.4 },
      { topic: 'Kheyre 2024', type: 'Political Sentiment', date: 'Oct 24, 2023 · 12:15', lang: 'SOMALI', score: 85.1 },
      { topic: 'Somalia FinTech Summit', type: 'Economy', date: 'Oct 24, 2023 · 09:44', lang: 'ENGLISH', score: 76.8 },
      { topic: 'Abaaraha 2023 Update', type: 'Environment', date: 'Oct 23, 2023 · 21:02', lang: 'SOMALI', score: 68.2 },
    ]
  },
  '7 DAYS': {
    total: '8,432',
    avg: '81.2',
    top: 'MOGADISHU, SO',
    trends: [
      { topic: 'Mogadishu Tech Week', type: 'Technology', date: 'Oct 18, 2023 · 10:15', lang: 'ENGLISH', score: 94.7 },
      { topic: 'Shilling Inflation', type: 'Economy', date: 'Oct 16, 2023 · 08:30', lang: 'SOMALI', score: 89.3 },
      { topic: 'Horn of Africa Trade', type: 'Business', date: 'Oct 18, 2023 · 14:20', lang: 'ENGLISH', score: 82.1 },
      { topic: 'Roobka Deyrta', type: 'Weather & Environment', date: 'Oct 15, 2023 · 18:45', lang: 'SOMALI', score: 71.5 },
    ]
  },
  '30 DAYS': {
    total: '42,109',
    avg: '75.9',
    top: 'GAROWE, SO',
    trends: [
      { door: 'open', topic: 'Puntland Elections', type: 'Politics', date: 'Sep 28, 2023 · 11:00', lang: 'SOMALI', score: 96.5 },
      { topic: 'Africa Climate Summit', type: 'Environment', date: 'Sep 25, 2023 · 16:30', lang: 'ENGLISH', score: 91.2 },
      { topic: 'Jubaland Security', type: 'National Security', date: 'Oct 02, 2023 · 09:12', lang: 'SOMALI', score: 84.8 },
      { topic: 'Somali Diaspora GDP', type: 'Economy', date: 'Sep 20, 2023 · 13:40', lang: 'ENGLISH', score: 79.4 },
    ]
  },
  'CUSTOM': {
    total: '105,441',
    avg: '88.3',
    top: 'DJIBOUTI, DJI',
    trends: [
      { topic: 'Historical Election Archive', type: 'National Politics', date: 'May 15, 2022 · 08:00', lang: 'SOMALI', score: 98.9 },
      { topic: 'Horn Telecom Expansion', type: 'Technology', date: 'Jan 10, 2023 · 15:20', lang: 'ENGLISH', score: 92.3 },
      { topic: 'Drought Declaration', type: 'Environment', date: 'Nov 05, 2022 · 12:45', lang: 'SOMALI', score: 87.5 },
    ]
  }
}

const History = () => {
  const { range } = useDateRange()
  const { t } = useLanguage()
  const currentData = MOCK_DATA[range] || MOCK_DATA['24 HOURS']

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 md:gap-0 mb-8 md:mb-10 w-full">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-extrabold text-brand-secondary uppercase tracking-widest mb-2">
            <div className="w-2 h-2 rounded-full bg-brand-secondary"></div>
            ARCHIVE SYSTEMS ACTIVE
          </div>
          <h1 className="text-4xl font-extrabold text-slate-950 dark:text-white mb-2 tracking-tight">{t('history')}</h1>
          <p className="text-slate-500 dark:text-slate-200">Chronological audit of detected semantic shifts and<br/>regional trending topics.</p>
        </div>
        
        <DateFilter />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-y-[2px] md:gap-[2px] md:gap-y-0 bg-slate-100 dark:bg-slate-800 rounded-sm overflow-hidden border border-slate-100 dark:border-slate-800 shadow-sm mb-8 transition-colors">
        <div className="bg-white dark:bg-slate-900 p-6 relative">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">TOTAL TRENDS</h3>
          <div className="text-4xl font-light text-slate-800 dark:text-slate-100">{currentData.total}</div>
          <div className="absolute right-4 bottom-4 text-7xl font-bold text-slate-50/80 dark:text-slate-800/30 -z-0 pointer-events-none">01</div>
        </div>
        <div className="bg-white dark:bg-slate-900 p-6 relative">
           <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">AVG. SCORE</h3>
          <div className="text-4xl font-light text-slate-800 dark:text-slate-100">{currentData.avg}</div>
          <div className="absolute right-4 bottom-4 text-7xl font-bold text-slate-50/80 dark:text-slate-800/30 -z-0 pointer-events-none">02</div>
        </div>
        <div className="bg-white dark:bg-slate-900 p-6 relative">
          <div className="flex justify-between items-start">
             <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">TOP REGION</h3>
             <span className="text-[11px] font-bold text-brand-secondary">&#8599; +12%</span>
          </div>
          <div className="text-2xl font-light text-slate-800 dark:text-slate-100 tracking-tight mt-2">{currentData.top}</div>
          <div className="absolute right-4 bottom-4 text-7xl font-bold text-slate-50/80 dark:text-slate-800/30 -z-0 pointer-events-none">03</div>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm transition-colors w-full overflow-hidden">
        <div className="overflow-x-auto w-full">
          <div className="min-w-[800px] w-full">
            <div className="grid grid-cols-12 text-[10px] font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 p-4">
              <div className="col-span-5">TOPIC NAME</div>
              <div className="col-span-2 text-center">DETECTED DATE/TIME</div>
          <div className="col-span-2 text-center">LANGUAGE</div>
          <div className="col-span-2 text-center">TREND SCORE</div>
          <div className="col-span-1 text-center">ACTION</div>
        </div>

        <div className="flex flex-col">
           {currentData.trends.map((item, idx) => (
             <div key={idx} className="grid grid-cols-12 items-center p-4 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
               <div className="col-span-5">
                 <div className="text-[15px] font-bold text-slate-900 dark:text-slate-200">{item.topic}</div>
                 <div className="text-[11px] text-slate-400 mt-0.5">{item.type}</div>
               </div>
               <div className="col-span-2 text-center">
                  <div className="text-[11px] font-medium text-slate-600 dark:text-slate-200 whitespace-pre-line leading-relaxed">
                    {item.date.replace(' · ', '\n')}
                  </div>
               </div>
               <div className="col-span-2 text-center flex justify-center">
                  <span className="border border-brand-secondary dark:border-brand-secondary text-brand-secondary dark:text-brand-secondary bg-brand-secondary/10 dark:bg-brand-secondary/30 hover:bg-brand-secondary dark:hover:bg-brand-secondary/50 transition-colors cursor-pointer text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full">
                    {item.lang}
                  </span>
               </div>
               <div className="col-span-2 flex items-center justify-center gap-3">
                 <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                   <div className="h-full bg-brand-secondary rounded-full" style={{ width: `${item.score}%` }}></div>
                 </div>
                 <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{item.score}</span>
               </div>
               <div className="col-span-1 flex justify-center">
                 <button className="text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                   <Eye size={18} />
                 </button>
               </div>
             </div>
           ))}
        </div>

            <div className="p-4 flex justify-center bg-slate-50/50 dark:bg-slate-800/20">
              <button className="bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-[10px] font-extrabold uppercase tracking-widest px-6 py-3 rounded-sm transition-colors flex items-center gap-2">
                LOAD ARCHIVE 10.23.23 <span className="transform rotate-90">&raquo;</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default History
