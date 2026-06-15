import React, { useState, useEffect } from 'react'
import { MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { getRawTweets } from '../services/api'
import { rangeToQueryParams } from '../utils/dateRange'

const XIcon = ({ size = 24, className }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="currentColor"
    className={className}
  >
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.008 5.975H5.034z"/>
  </svg>
)

const Tweets = () => {
  const { t, language } = useLanguage();
  const { range, customDates } = useDateRange();
  const [filter, setFilter] = useState('ALL')
  const [tweets, setTweets] = useState([])
  const [loading, setLoading] = useState(true)
  
  const fetchTweets = async () => {
    setLoading(true)
    try {
      let data = [];
      const langsToFetch = filter === 'ALL' ? ['en', 'so'] : [filter === 'ENGLISH' ? 'en' : 'so'];
      const dateParams = rangeToQueryParams(range, customDates);
      
      for (let lng of langsToFetch) {
        let result = await getRawTweets(lng, dateParams, 50); // Get 50 tweets per lang
        data = [...data, ...result];
      }
      
      // Sort combined by timestamp descending
      data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      setTweets(data);
    } catch (error) {
      console.error('Error fetching raw tweets:', error)
      setTweets([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTweets()
    // Optionally we could set up an interval to poll for new tweets
    const interval = setInterval(fetchTweets, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, [filter, range, customDates])

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 md:gap-0 mb-6 w-full">
        <div>
          <h1 className="text-3xl font-extrabold text-brand-primary dark:text-white mb-2 flex items-center gap-3">
            <XIcon className="text-slate-900 dark:text-white" size={32} />
            Raw Tweets
          </h1>
          <p className="text-slate-500 dark:text-slate-200">Live stream of raw tweets from the ingestion engine.</p>
        </div>
        <div className="flex flex-col items-end gap-3 w-full md:w-auto">
          <DateFilter />
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 pb-2 transition-colors duration-300 w-full overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 sm:gap-0">
          <h2 className="text-lg font-bold text-brand-primary dark:text-slate-100">Latest Activity</h2>
          
          <div className="flex gap-2">
            {[
              { id: 'ALL', label: language === 'so' ? 'DHAMAAN' : 'ALL' },
              { id: 'ENGLISH', label: language === 'so' ? 'INGIRIISI' : 'ENGLISH' },
              { id: 'SOMALI', label: language === 'so' ? 'SOOMAALI' : 'SOMALI' }
            ].map(f => (
              <button 
                key={f.id} 
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition-colors ${filter === f.id ? 'bg-brand-secondary text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        
        {loading && tweets.length === 0 ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold">Loading real-time tweets...</div>
        ) : tweets.length === 0 ? (
          <div className="py-10 text-center text-slate-500 dark:text-slate-400 text-sm font-bold">No tweets ingested yet. Ensure background stream is active.</div>
        ) : (
          <div className="overflow-x-auto w-full">
            <div className="min-w-[700px] w-full">
              <div className="grid grid-cols-12 text-[10px] font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 pb-3 px-2">
                <div className="col-span-8 pl-4">TWEET CONTENT</div>
                <div className="col-span-1 text-center border-x border-slate-100 dark:border-slate-800">LANG</div>
                <div className="col-span-3 text-center pr-2">TIMESTAMP</div>
              </div>

              <div className="flex flex-col">
                {tweets.map((t, idx) => (
                  <div 
                    key={t._id || idx}
                    className="grid grid-cols-12 items-center py-4 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors px-2 rounded-xl"
                  >
                    <div className="col-span-8 pl-4 pr-12 flex items-start gap-3">
                      <MessageSquare className="text-slate-300 mt-1 flex-shrink-0" size={18} />
                      <div>
                        <div className="text-[14px] font-medium text-slate-800 dark:text-slate-200">{t.text}</div>
                        <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">ID: {t.tweet_id}</div>
                      </div>
                    </div>
                    <div className="col-span-1 text-center border-x border-slate-100 dark:border-slate-800 flex justify-center h-full items-center">
                      <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/30 dark:text-brand-secondary text-[10px] font-bold px-2 py-1 rounded-sm uppercase">{t.language}</span>
                    </div>
                    <div className="col-span-3 text-center flex flex-col justify-center items-center pr-2 text-slate-500 dark:text-slate-400 text-xs">
                       {new Date(t.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Tweets
