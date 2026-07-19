import React, { useState, useEffect } from 'react'
import { Hash } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { useDateRange } from '../contexts/DateRangeContext'
import { getTrends, getTrendingKeywords, getTweetStats } from '../services/api'
import DateFilter from '../components/DateFilter'
import { rangeToQueryParams } from '../utils/dateRange'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, LabelList,
  PieChart, Pie, Cell
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
  
  const [trendingKeywords, setTrendingKeywords] = useState([])
  const [keywordsLoading, setKeywordsLoading] = useState(true)
  const [keywordsError, setKeywordsError] = useState(false)

  const COLORS = {
    brandPrimary: '#1E3A8A',
    brandSecondary: '#0EA5E9',
  }

  const fetchDashboardData = async () => {
    setLoading(true)
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
          <h1 className="text-2xl font-bold text-brand-primary dark:text-white">{t('dashboard') || 'Dashboard'}</h1>
        </div>
        <div className="flex flex-col items-start xl:items-end w-full xl:w-auto">
          <div className="flex flex-wrap items-center gap-3 w-full justify-start xl:justify-end">
            <DateFilter />
          </div>
        </div>
      </div>

      {/* Top Statistics Cards */}
      {stats.totalTweets === 0 && (
        <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 p-4 rounded-xl mb-6 text-sm flex items-center gap-3 italic">
          No data collected yet. Charts will populate once tweets are available.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Tweets" value={stats.totalTweets} icon={XIcon} subtext="All collected tweets" subtextColor="text-slate-400" iconColor="text-brand-primary dark:text-white" />
        <StatCard title="English Tweets" value={stats.totalEnglishTweets} icon={XIcon} subtext={`${stats.totalTweets > 0 ? ((stats.totalEnglishTweets / stats.totalTweets) * 100).toFixed(1) : '0.0'}% of total`} subtextColor="text-brand-primary" iconColor="text-brand-primary" />
        <StatCard title="Somali Tweets" value={stats.totalSomaliTweets} icon={XIcon} subtext={`${stats.totalTweets > 0 ? ((stats.totalSomaliTweets / stats.totalTweets) * 100).toFixed(1) : '0.0'}% of total`} subtextColor="text-brand-secondary" iconColor="text-brand-secondary" />
        <StatCard title="Trending Topics" value={stats.trendingTopics} icon={Hash} subtext="Detected topics" subtextColor="text-slate-400" iconColor="text-brand-secondary" />
      </div>


      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Language Distribution donut chart */}
        <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 transition-colors duration-300 min-h-[320px] flex flex-col">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">Language Distribution</h2>
          {stats.totalTweets === 0 ? (
            <div className="flex-1 flex items-center justify-center text-center">
              <p className="text-xs text-slate-400 dark:text-slate-500 italic">No tweet data yet.</p>
            </div>
          ) : (() => {
            const langData = [
              { name: 'English', value: stats.totalEnglishTweets, color: '#1E3A8A' },
              { name: 'Somali',  value: stats.totalSomaliTweets,  color: '#0EA5E9' },
            ]
            const total = stats.totalTweets
            return (
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <div className="h-[200px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={langData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {langData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                        itemStyle={{ fontSize: '12px', fontWeight: 'bold', color: '#f8fafc' }}
                        formatter={(value, name) => [`${value.toLocaleString()} tweets (${((value/total)*100).toFixed(1)}%)`, name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex gap-6 text-xs">
                  {langData.map((d) => (
                    <div key={d.name} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: d.color }} />
                      <span className="text-slate-600 dark:text-slate-300 font-medium">{d.name}</span>
                      <span className="font-bold text-slate-800 dark:text-white">{((d.value / total) * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
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
                    'text-brand-primary dark:text-sky-400 font-bold',
                    'text-brand-secondary dark:text-brand-secondary font-semibold',
                    'text-slate-600 dark:text-slate-300 font-medium',
                    'text-brand-primary/70 dark:text-sky-300 font-semibold',
                    'text-brand-secondary/80 dark:text-cyan-400 font-medium',
                    'text-slate-500 dark:text-slate-400 font-bold',
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
          <h2 className="text-sm font-semibold text-brand-primary dark:text-slate-200 mb-4">Top Topics</h2>
          {topTopics.length === 0 ? (
            <div className="h-[250px] flex items-center justify-center">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold italic">No data available for the selected period</p>
            </div>
          ) : (
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topTopics} layout="vertical" margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="name"
                    type="category"
                    fontSize={10}
                    fontWeight={600}
                    tick={{ fill: '#64748b' }}
                    tickLine={false}
                    axisLine={false}
                    width={72}
                  />
                  <RechartsTooltip
                    cursor={{ fill: 'rgba(14, 165, 233, 0.06)' }}
                    contentStyle={{ backgroundColor: '#0F172A', border: 'none', borderRadius: '10px', color: '#f8fafc', padding: '8px 14px' }}
                    itemStyle={{ fontSize: '12px', fontWeight: 'bold', color: '#0EA5E9' }}
                    labelStyle={{ fontSize: '11px', color: '#94a3b8', marginBottom: '2px' }}
                  />
                  <Bar dataKey="count" name="Score" radius={[0, 6, 6, 0]} barSize={14}>
                    {topTopics.map((_, i) => (
                      <Cell key={i} fill={i % 2 === 0 ? '#1E3A8A' : '#0EA5E9'} />
                    ))}
                    <LabelList dataKey="count" position="right" formatter={(val) => val.toLocaleString()} style={{ fontSize: '10px', fontWeight: 700, fill: '#64748b' }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard

