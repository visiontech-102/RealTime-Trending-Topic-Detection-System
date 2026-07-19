import React, { useState, useEffect } from 'react'
import { Search, TrendingUp, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { useDateRange } from '../contexts/DateRangeContext'
import { getTrends, filterTrends } from '../services/api'
import DateFilter from '../components/DateFilter'
import { rangeToQueryParams } from '../utils/dateRange'

const Trending = () => {
  const { t, language } = useLanguage();
  const { range, customDates } = useDateRange();
  const [filter, setFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedRow, setExpandedRow] = useState(null)
  
  const fetchTrends = async (keyword = '') => {
    setLoading(true)
    try {
      // If ALL is selected, we might want to fetch both, but the API handles lang=en or lang=so.
      // If we select ALL, let's fetch EN and SO and combine them.
      let data = [];
      const langsToFetch = filter === 'ALL' ? ['en', 'so'] : [filter === 'ENGLISH' ? 'en' : 'so'];
      
      const dateParams = rangeToQueryParams(range, customDates)
      for (let lng of langsToFetch) {
        let result = [];
        if (keyword) {
          result = await filterTrends(keyword, lng);
        } else {
          result = await getTrends(lng, dateParams);
        }
        data = [...data, ...result];
      }
      
      // Sort combined by score
      data.sort((a, b) => b.score - a.score);
      setTrends(data);
    } catch (error) {
      console.error('Error fetching trends:', error)
      setTrends([])
    } finally {
      setLoading(false)
    }
  }

  // Fetch real trends on filter or search change
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchTrends(searchQuery)
    }, 500)

    return () => clearTimeout(delayDebounceFn)
  }, [filter, searchQuery, range, customDates])

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 md:gap-0 mb-6 w-full">
        <div>
          <h1 className="text-3xl font-extrabold text-brand-primary dark:text-white mb-2">{t('trending')}</h1>
        </div>
        <div className="flex flex-col items-end gap-3 w-full md:w-1/3">
          {/* Use Case: Search Trends by Keyword */}
          <div className="relative w-full">
             <input 
               type="text" 
               placeholder="Search keywords..." 
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-4 py-2 pl-10 text-sm focus:outline-none focus:border-brand-secondary text-slate-800 dark:text-slate-200"
             />
             <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
          </div>
          <DateFilter />
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 pb-2 transition-colors duration-300 w-full overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 sm:gap-0">
          <h2 className="text-lg font-bold text-brand-primary dark:text-slate-100">{t('trends') || 'Top Trending Topics'}</h2>
          
          {/* Use Case: Filter Topics by Language */}
          <div className="flex gap-2">
            {[
              { id: 'ALL', label: language === 'so' ? 'DHAMAAN' : 'ALL' },
              { id: 'ENGLISH', label: language === 'so' ? 'INGIRIISI' : 'ENGLISH' },
              { id: 'SOMALI', label: language === 'so' ? 'SOOMAALI' : 'SOMALI' }
            ].map(f => (
              <button 
                key={f.id} 
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition-colors ${filter === f.id ? 'bg-brand-primary text-white' : 'bg-slate-100 dark:bg-slate-800 text-brand-primary dark:text-slate-300 hover:bg-brand-primary hover:text-white dark:hover:bg-brand-secondary dark:hover:text-slate-900'}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        
        {loading ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold">Loading real-time data...</div>
        ) : trends.length === 0 ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold">No trends discovered yet. Ensure background stream is active.</div>
        ) : (
          <div className="overflow-x-auto w-full">
            <div className="min-w-[700px] w-full">
              <div className="grid grid-cols-12 text-[10px] font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 pb-3 px-2">
                <div className="col-span-1 border-r border-slate-100 dark:border-slate-800">RANK</div>
                <div className="col-span-6 pl-4">TOPIC ENTITY & KEYWORDS</div>
                <div className="col-span-1 text-center border-x border-slate-100 dark:border-slate-800">LANG</div>
                <div className="col-span-3 text-center border-r border-slate-100 dark:border-slate-800">ENGAGEMENT SCORE</div>
                <div className="col-span-1 text-right pr-2">INFO</div>
              </div>

              <div className="flex flex-col">
                {trends.map((t, idx) => (
                  <React.Fragment key={t._id || idx}>
                    <div 
                      onClick={() => setExpandedRow(expandedRow === idx ? null : idx)}
                      className="grid grid-cols-12 items-center py-3 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors px-2 rounded-xl cursor-pointer"
                    >
                      <div className="col-span-1 border-r border-slate-100 dark:border-slate-800 text-3xl font-light text-slate-300 dark:text-slate-700">
                        {String(idx + 1).padStart(2, '0')}
                      </div>
                      <div className="col-span-6 pl-4 pr-12">
                        <div className="text-[15px] font-bold text-brand-primary dark:text-slate-200">{t.label || t.topic_name}</div>
                        <div className="text-xs text-slate-400 dark:text-slate-300 mt-0.5">{t.top_keywords?.join(', ')}</div>
                      </div>
                      <div className="col-span-1 text-center border-x border-slate-100 dark:border-slate-800 flex justify-center">
                        <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/30 dark:text-brand-secondary text-[10px] font-bold px-2 py-1 rounded-sm uppercase">{(t.language || '').toUpperCase()}</span>
                      </div>
                      <div className="col-span-3 text-center border-r border-slate-100 dark:border-slate-800 flex flex-col justify-center items-center">
                        <div className="flex items-center gap-2">
                           <TrendingUp size={16} className="text-brand-secondary"/>
                           <span className="text-[14px] font-bold text-slate-800 dark:text-slate-300">{t.score ? t.score.toFixed(1) : 'N/A'}</span>
                        </div>
                        <span className="text-[9px] text-slate-400 dark:text-slate-400 uppercase mt-1">Velocity Score</span>
                      </div>
                      <div className="col-span-1 flex items-center justify-end pr-2 text-slate-400 dark:text-slate-300">
                         {expandedRow === idx ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </div>
                    </div>
                    {/* Use Case 4: View Topic Summary */}
                    {expandedRow === idx && (
                      <div className="bg-slate-50 dark:bg-slate-800/30 p-4 pl-16 rounded-b-xl border-b border-slate-100 dark:border-slate-800 text-sm shadow-inner transition-all">
                        <h4 className="font-bold text-xs text-brand-secondary uppercase tracking-widest mb-2">Topic Summary (Representative Tweets)</h4>
                        <ul className="list-disc pl-5 space-y-2 text-slate-600 dark:text-slate-300 text-xs leading-relaxed">
                          {t.representative_docs && t.representative_docs.length > 0 ? (
                            t.representative_docs.map((doc, dIdx) => (
                              <li key={dIdx}>{doc}</li>
                            ))
                          ) : (
                            <li>No representative context available.</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Trending
