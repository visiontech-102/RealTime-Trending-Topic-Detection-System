import React, { useState, useEffect } from 'react'
import { Eye, Loader2 } from 'lucide-react'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { useLanguage } from '../contexts/LanguageContext'
import { getHistory } from '../services/api'
import { rangeToQueryParams } from '../utils/dateRange'

const History = () => {
  const { range, customDates } = useDateRange()
  const { t } = useLanguage()
  
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        let data = [];
        const dateParams = rangeToQueryParams(range, customDates)
        const langsToFetch = ['en', 'so'];
        
        for (let lng of langsToFetch) {
          let result = await getHistory(lng, dateParams);
          data = [...data, ...result];
        }
        
        // Sort combined by timestamp descending
        data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setTrends(data);
      } catch (error) {
        console.error('Error fetching history:', error)
        setTrends([])
      } finally {
        setLoading(false)
      }
    }

    fetchHistory()
  }, [range, customDates])

  const total = trends.length;
  const avg = trends.length ? (trends.reduce((acc, t) => acc + (t.score || 0), 0) / trends.length).toFixed(1) : '0.0';
  const topTrend = trends.length > 0 ? trends.sort((a,b) => b.score - a.score)[0] : null;
  const top = topTrend ? (topTrend.label || topTrend.topic_name) : 'N/A';

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 md:gap-0 mb-8 md:mb-10 w-full">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-extrabold text-brand-secondary uppercase tracking-widest mb-2">
            <div className="w-2 h-2 rounded-full bg-brand-secondary animate-pulse"></div>
            LIVE ARCHIVE SYSTEMS ACTIVE
          </div>
          <h1 className="text-4xl font-extrabold text-slate-950 dark:text-white mb-2 tracking-tight">{t('history')}</h1>
          <p className="text-slate-500 dark:text-slate-200">Chronological audit of detected semantic shifts and<br/>regional trending topics.</p>
        </div>
        
        <DateFilter />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-y-[2px] md:gap-[2px] md:gap-y-0 bg-slate-100 dark:bg-slate-800 rounded-sm overflow-hidden border border-slate-100 dark:border-slate-800 shadow-sm mb-8 transition-colors">
        <div className="bg-white dark:bg-slate-900 p-6 relative">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">TOTAL TRENDS FETCHED</h3>
          <div className="text-4xl font-light text-slate-800 dark:text-slate-100">{total}</div>
          <div className="absolute right-4 bottom-4 text-7xl font-bold text-slate-50/80 dark:text-slate-800/30 -z-0 pointer-events-none">01</div>
        </div>
        <div className="bg-white dark:bg-slate-900 p-6 relative">
           <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">AVG. SCORE</h3>
          <div className="text-4xl font-light text-slate-800 dark:text-slate-100">{avg}</div>
          <div className="absolute right-4 bottom-4 text-7xl font-bold text-slate-50/80 dark:text-slate-800/30 -z-0 pointer-events-none">02</div>
        </div>
        <div className="bg-white dark:bg-slate-900 p-6 relative">
          <div className="flex justify-between items-start">
             <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">TOP TRENDING TOPIC</h3>
             <span className="text-[11px] font-bold text-brand-secondary">&#8599; LIVE</span>
          </div>
          <div className="text-2xl font-light text-slate-800 dark:text-slate-100 tracking-tight mt-2 truncate pr-16">{top}</div>
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

        {loading ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold flex justify-center items-center gap-2">
            <Loader2 size={18} className="animate-spin" /> Fetching real-time history data...
          </div>
        ) : trends.length === 0 ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold">No history data available.</div>
        ) : (
          <div className="flex flex-col">
             {trends.map((item, idx) => (
               <div key={item._id || idx} className="grid grid-cols-12 items-center p-4 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                 <div className="col-span-5">
                   <div className="text-[15px] font-bold text-slate-900 dark:text-slate-200">{item.label || item.topic_name}</div>
                   <div className="text-[11px] text-slate-400 mt-0.5">{item.top_keywords?.join(', ')}</div>
                 </div>
                 <div className="col-span-2 text-center">
                    <div className="text-[11px] font-medium text-slate-600 dark:text-slate-200 whitespace-pre-line leading-relaxed">
                      {new Date(item.timestamp).toLocaleString()}
                    </div>
                 </div>
                 <div className="col-span-2 text-center flex justify-center">
                    <span className="border border-brand-secondary dark:border-brand-secondary text-brand-secondary dark:text-brand-secondary bg-brand-secondary/10 dark:bg-brand-secondary/30 hover:bg-brand-secondary dark:hover:bg-brand-secondary/50 transition-colors cursor-pointer text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full">
                      {item.language}
                    </span>
                 </div>
                 <div className="col-span-2 flex items-center justify-center gap-3">
                   <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                     <div className="h-full bg-brand-secondary rounded-full" style={{ width: `${Math.min(item.score, 100)}%` }}></div>
                   </div>
                   <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{item.score ? item.score.toFixed(1) : 'N/A'}</span>
                 </div>
                 <div className="col-span-1 flex justify-center">
                   <button className="text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                     <Eye size={18} />
                   </button>
                 </div>
               </div>
             ))}
          </div>
        )}

            <div className="p-4 flex justify-center bg-slate-50/50 dark:bg-slate-800/20">
              <button onClick={() => {}} className="bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-[10px] font-extrabold uppercase tracking-widest px-6 py-3 rounded-sm transition-colors flex items-center gap-2">
                LOAD MORE ARCHIVE <span className="transform rotate-90">&raquo;</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default History

