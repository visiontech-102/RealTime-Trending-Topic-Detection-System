import React, { useState, useEffect } from 'react'
import { Hash } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { useDateRange } from '../contexts/DateRangeContext'
import { getTrends, getTopicTrends, getTrendingKeywords, getTweetStats } from '../services/api'
import DateFilter from '../components/DateFilter'
import { rangeToQueryParams } from '../utils/dateRange'
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Legend, Tooltip as RechartsTooltip, ResponsiveContainer, LabelList
} from 'recharts'

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

const Dashboard = () => {
  const { t } = useLanguage();
  const { range, customDates } = useDateRange();
  const [filter] = useState('ALL')
  const [loading, setLoading] = useState(true)
  
  // Data states
  const [stats, setStats] = useState({
    totalTweets: 0,
    totalEnglishTweets: 0,
    totalSomaliTweets: 0,
    trendingTopics: 0
  })
  const [topTopics, setTopTopics] = useState([])
  
  const [topicTrends, setTopicTrends] = useState([])
  const [topicTrendsLoading, setTopicTrendsLoading] = useState(true)
  const [topicTrendsError, setTopicTrendsError] = useState(false)
  
  const [trendingKeywords, setTrendingKeywords] = useState([])
  const [keywordsLoading, setKeywordsLoading] = useState(true)
  const [keywordsError, setKeywordsError] = useState(false)

  const COLORS = {
    brandPrimary: '#3b82f6', // text-blue-500
  }

  const fetchDashboardData = async () => {
    setLoading(true)
    setTopicTrendsLoading(true)
    setTopicTrendsError(false)
    setKeywordsLoading(true)
    setKeywordsError(false)
    
    const dateParams = rangeToQueryParams(range, customDates)
    
    try {
      const statsData = await getTweetStats(dateParams);
      let data = [];
      const langsToFetch = filter === 'ALL' ? ['en', 'so'] : [filter === 'ENGLISH' ? 'en' : 'so'];
      
      for (let lng of langsToFetch) {
        const result = await getTrends(lng, dateParams);
        data = [...data, ...result];
      }
      
      data.sort((a, b) => b.score - a.score);
      
      if (data.length === 0) {
        setStats({
          totalTweets: statsData.totalTweets || 0,
          totalEnglishTweets: statsData.totalEnglishTweets || 0,
          totalSomaliTweets: statsData.totalSomaliTweets || 0,
          trendingTopics: 0
        });
        setTopTopics([]);
      } else {
        setStats({
          totalTweets: statsData.totalTweets || 0,
          totalEnglishTweets: statsData.totalEnglishTweets || 0,
          totalSomaliTweets: statsData.totalSomaliTweets || 0,
          trendingTopics: data.length
        });

        setTopTopics(data.slice(0, 8).map(t => ({
          name: (t.label || t.topic_name).length > 15 ? (t.label || t.topic_name).substring(0, 15) + '...' : (t.label || t.topic_name),
          count: Math.floor(t.score)
        })));
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }

    try {
      const trendsData = await getTopicTrends(dateParams);
      setTopicTrends(trendsData || []);
    } catch (error) {
      console.error('Error fetching topic trends:', error);
      setTopicTrendsError(true);
    } finally {
      setTopicTrendsLoading(false);
    }

    try {
      const keywordsData = await getTrendingKeywords(dateParams);
      setTrendingKeywords(keywordsData || []);
    } catch (error) {
      console.error('Error fetching keywords:', error);
      setKeywordsError(true);
    } finally {
      setKeywordsLoading(false);
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [filter, range, customDates])

  const StatCard = ({ title, value, icon: Icon, subtext, subtextColor, iconColor }) => (
    <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 transition-all duration-300 hover:shadow-sm hover:-translate-y-1">
      <div className="flex justify-between items-center mb-1">
        <h3 className="text-slate-800 dark:text-slate-200 text-sm font-semibold">{title}</h3>
        <Icon className={iconColor} size={22} strokeWidth={1.5} />
      </div>
      <div>
        <p className="text-[28px] font-bold text-slate-900 dark:text-white leading-tight mb-1">{value.toLocaleString()}</p>
        <div className={`text-xs ${subtextColor} font-medium`}>
          {subtext}
        </div>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="animate-in fade-in duration-500 w-full mb-8">
        <div className="flex items-center justify-center h-[60vh]">
          <div className="animate-pulse flex flex-col items-center">
            <div className="w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-slate-500 dark:text-slate-400 font-bold tracking-widest text-sm uppercase">Loading Dashboard...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      {/* Header */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-6 xl:gap-0 mb-6 w-full">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{t('dashboard') || 'Dashboard'}</h1>
        </div>
        <div className="flex flex-col items-start xl:items-end w-full xl:w-auto">
          <div className="flex flex-wrap items-center gap-3 w-full justify-start xl:justify-end">
            <DateFilter />
          </div>
        </div>
      </div>

      {/* Top Statistics Cards */}
      {stats.totalTweets === 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 p-4 rounded-xl mb-6 font-bold flex items-center gap-3">
          <span>⚠️</span> No real-time data or historical data found in the database. Ensure the Twitter API stream is running.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Tweets" value={stats.totalTweets} icon={XIcon} subtext="↑ 15.3% vs last 7 days" subtextColor="text-emerald-500" iconColor="text-slate-900 dark:text-white" />
        <StatCard title="Total English Tweets" value={stats.totalEnglishTweets} icon={XIcon} subtext={`${stats.totalTweets > 0 ? ((stats.totalEnglishTweets / stats.totalTweets) * 100).toFixed(1) : '0.0'}%`} subtextColor="text-blue-500" iconColor="text-blue-500" />
        <StatCard title="Total Somali Tweets" value={stats.totalSomaliTweets} icon={XIcon} subtext={`${stats.totalTweets > 0 ? ((stats.totalSomaliTweets / stats.totalTweets) * 100).toFixed(1) : '0.0'}%`} subtextColor="text-emerald-500" iconColor="text-emerald-500" />
        <StatCard title="Trending Topics" value={stats.trendingTopics} icon={Hash} subtext="Active topics" subtextColor="text-slate-500" iconColor="text-purple-600" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Topic Trends line chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 transition-colors duration-300 min-h-[320px] flex flex-col">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">Topic Trends</h2>
          {topicTrendsLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center py-10">
              <div className="w-6 h-6 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mb-2"></div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Loading Trends...</p>
            </div>
          ) : topicTrendsError ? (
            <div className="flex-1 flex items-center justify-center py-10 text-center">
              <p className="text-xs text-red-500 font-bold">Failed to load topic trends.</p>
            </div>
          ) : topicTrends.length === 0 ? (
            <div className="flex-1 flex items-center justify-center py-10 text-center">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold italic">No data available for the selected period</p>
            </div>
          ) : (
            <div className="h-[250px] w-full mt-auto animate-in fade-in duration-300">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={topicTrends} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" className="dark:opacity-20" />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} dy={10} />
                  <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                    itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
                  />
                  <Legend verticalAlign="top" align="center" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '10px', paddingBottom: '10px' }} />
                  {(() => {
                    const topicKeys = topicTrends.length > 0 ? Object.keys(topicTrends[0]).filter(k => k !== 'date') : [];
                    const categoryColors = {
                      'AI': '#3b82f6',
                      'Security': '#ef4444',
                      'Politics': '#a855f7',
                      'Economy': '#eab308',
                      'Business': '#10b981',
                      'Sports': '#f97316',
                      'Health': '#ec4899',
                      'Education': '#14b8a6',
                      'Technology': '#6366f1',
                      'Climate': '#06b6d4'
                    };
                    const getCategoryColor = (key, idx) => {
                      if (categoryColors[key]) return categoryColors[key];
                      const defaults = ['#3b82f6', '#10b981', '#ef4444', '#a855f7', '#eab308', '#f97316', '#ec4899', '#14b8a6', '#6366f1', '#06b6d4'];
                      return defaults[idx % defaults.length];
                    };
                    return topicKeys.map((key, idx) => (
                      <Line 
                        key={key}
                        type="monotone" 
                        dataKey={key} 
                        stroke={getCategoryColor(key, idx)} 
                        strokeWidth={2} 
                        activeDot={{ r: 4 }} 
                        dot={{ r: 2 }} 
                      />
                    ));
                  })()}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Trending Now word cloud */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 transition-colors duration-300 min-h-[320px] flex flex-col">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">Trending Now</h2>
          {keywordsLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center py-10">
              <div className="w-6 h-6 border-2 border-brand-primary border-t-transparent rounded-full animate-spin mb-2"></div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Loading Cloud...</p>
            </div>
          ) : keywordsError ? (
            <div className="flex-1 flex items-center justify-center py-10 text-center">
              <p className="text-xs text-red-500 font-bold">Failed to load trending keywords.</p>
            </div>
          ) : trendingKeywords.length === 0 ? (
            <div className="flex-1 flex items-center justify-center py-10 text-center">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold italic">No trending keywords for the selected period</p>
            </div>
          ) : (
            <div className="h-[250px] w-full flex items-center justify-center p-2 mt-auto animate-in fade-in duration-300">
              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 overflow-hidden max-h-full">
                {trendingKeywords.map((kw, idx) => {
                  const colors = [
                    'text-blue-500 dark:text-blue-400 font-bold',
                    'text-green-500 dark:text-green-400 font-medium',
                    'text-orange-500 dark:text-orange-400 font-semibold',
                    'text-purple-500 dark:text-purple-400 font-medium',
                    'text-teal-500 dark:text-teal-400 font-semibold',
                    'text-red-500 dark:text-red-400 font-bold',
                  ];
                  const colorClass = colors[idx % colors.length];
                  const sorted = [...trendingKeywords].sort((a, b) => b.value - a.value);
                  const max = sorted[0]?.value || 1;
                  const min = sorted[sorted.length - 1]?.value || 1;
                  const size = max === min ? 16 : 10 + ((kw.value - min) / (max - min)) * 16;
                  return (
                    <span
                      key={kw.text}
                      className={`${colorClass} hover:scale-110 transition-transform cursor-pointer`}
                      style={{ fontSize: `${size}px` }}
                      title={`Frequency: ${kw.value}`}
                    >
                      {kw.text}
                    </span>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Top Topics Horizontal Bar Chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 transition-colors duration-300">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">Top Topics</h2>
          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topTopics} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} width={70} />
                <RechartsTooltip 
                  cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ fontSize: '11px', fontWeight: 'bold' }}
                />
                <Bar dataKey="count" name="Tweets" fill={COLORS.brandPrimary} radius={[0, 4, 4, 0]} barSize={12}>
                  <LabelList dataKey="count" position="right" formatter={(val) => val.toLocaleString()} style={{ fontSize: '10px', fill: '#64748b' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {/* Custom X Axis labels for visual match */}
          <div className="flex justify-between pl-[80px] pr-8 text-[9px] text-slate-400 mt-1">
            <span>0</span>
            <span>500</span>
            <span>1K</span>
            <span>1.5K</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

