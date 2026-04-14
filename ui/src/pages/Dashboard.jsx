import React, { useState, useEffect } from 'react'
import { Search, TrendingUp, ArrowRight, ArrowDown } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { useLanguage } from '../contexts/LanguageContext'
import { useDateRange } from '../contexts/DateRangeContext'
import { getTrends } from '../services/api'
import DateFilter from '../components/DateFilter'

const INITIAL_DATA = [
  { time: '10:00', vol: 4000 },
  { time: '10:05', vol: 3000 },
  { time: '10:10', vol: 2000 },
  { time: '10:15', vol: 2780 },
  { time: '10:20', vol: 1890 },
  { time: '10:25', vol: 2390 },
  { time: '10:30', vol: 3490 },
];

const LANG_DATA = [
  { name: 'English', value: 65, color: '#1E3A8A' }, // Deep Blue
  { name: 'Somali', value: 35, color: '#0EA5E9' },  // Vibrant Cyan
];

const DASH_MOCK_DATA = {
  '24 HOURS': {
    stats: [
      { title: 'volume', val: '45.2K', change: '+12.5%', isUp: true },
      { title: 'keywords', val: '1,204', change: '+5.2%', isUp: true },
      { title: 'engagement', val: '8.4M', change: '-2.1%', isUp: false },
    ],
    trends: [
      { rank: '01', topic: '#HargeisaTechSummit', desc: 'Digital Infrastructure & Innovation', lang: 'SO', vol: '12.4K', momentum: '+142%', trend: 'up' },
      { rank: '02', topic: 'Regional Trade Agreement', desc: 'EAC Economic Policy Update', lang: 'EN', vol: '8.9K', momentum: '+88%', trend: 'up' },
      { rank: '03', topic: '#SomaliElection2024', desc: 'Political Discourse & Polling', lang: 'SO', vol: '7.2K', momentum: '+64%', trend: 'up' },
      { rank: '04', topic: 'Blue Economy Forum', desc: 'Maritime Sustainability Debates', lang: 'EN', vol: '5.1K', momentum: '+12%', trend: 'flat' },
    ]
  },
  '7 DAYS': {
    stats: [
      { title: 'volume', val: '280.5K', change: '+18.1%', isUp: true },
      { title: 'keywords', val: '5,630', change: '+11.4%', isUp: true },
      { title: 'engagement', val: '42.1M', change: '+5.8%', isUp: true },
    ],
    trends: [
      { rank: '01', topic: 'Horn of Africa Trade', desc: 'Business & Economy', lang: 'EN', vol: '84K', momentum: '+54%', trend: 'up' },
      { rank: '02', topic: 'Mogadishu Tech Week', desc: 'Innovation Showcase', lang: 'EN', vol: '72K', momentum: '+41%', trend: 'up' },
      { rank: '03', topic: 'Shilling Inflation', desc: 'Economy Update', lang: 'SO', vol: '45K', momentum: '-12%', trend: 'down' },
      { rank: '04', topic: 'Roobka Deyrta', desc: 'Weather Patterns', lang: 'SO', vol: '38K', momentum: '+89%', trend: 'up' },
    ]
  },
  '30 DAYS': {
    stats: [
      { title: 'volume', val: '1.2M', change: '-4.5%', isUp: false },
      { title: 'keywords', val: '18,400', change: '+2.1%', isUp: true },
      { title: 'engagement', val: '185M', change: '-8.2%', isUp: false },
    ],
    trends: [
      { rank: '01', topic: 'Africa Climate Summit', desc: 'Continental Environment', lang: 'EN', vol: '420K', momentum: '+120%', trend: 'up' },
      { rank: '02', topic: 'Puntland Elections', desc: 'Regional Voting', lang: 'SO', vol: '350K', momentum: '+180%', trend: 'up' },
      { rank: '03', topic: 'Somali Diaspora GDP', desc: 'Remittances', lang: 'EN', vol: '120K', momentum: 'STABLE', trend: 'flat' },
      { rank: '04', topic: 'Jubaland Security', desc: 'National Defense', lang: 'SO', vol: '85K', momentum: '-15%', trend: 'down' },
    ]
  },
  'CUSTOM RANGE': {
    stats: [
      { title: 'volume', val: '3.4M', change: '--', isUp: true },
      { title: 'keywords', val: '42,100', change: '--', isUp: true },
      { title: 'engagement', val: '450M', change: '--', isUp: true },
    ],
    trends: [
      { rank: '01', topic: 'Historical Election Archive', desc: 'National Data', lang: 'SO', vol: '890K', momentum: '+50%', trend: 'up' },
      { rank: '02', topic: 'Horn Telecom Expansion', desc: 'Infrastructure', lang: 'EN', vol: '620K', momentum: '+25%', trend: 'up' },
      { rank: '03', topic: 'Drought Declaration', desc: 'Climate Emergency', lang: 'SO', vol: '450K', momentum: '+15%', trend: 'up' },
      { rank: '04', topic: 'Tech Investment Fund', desc: 'Startups', lang: 'EN', vol: '320K', momentum: '+5%', trend: 'up' },
    ]
  }
};

const Dashboard = () => {
  const { t, language } = useLanguage();
  const { range } = useDateRange();
  const [filter, setFilter] = useState('ALL')
  const [chartData, setChartData] = useState(INITIAL_DATA)
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Fetch real trends
  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const lang = language === 'so' ? 'so' : 'en'
        const data = await getTrends(lang)
        setTrends(data)
      } catch (error) {
        console.error('Error fetching trends:', error)
        setTrends([])
      } finally {
        setLoading(false)
      }
    }
    fetchTrends()
  }, [language])

  // Live updating effect
  useEffect(() => {
    const interval = setInterval(() => {
      setChartData(prev => {
        const newData = [...prev];
        newData.shift();
        const lastTime = newData[newData.length - 1].time;
        const [hh, mm] = lastTime.split(':').map(Number);
        let nextMm = mm + 5;
        let nextHh = hh;
        if (nextMm >= 60) {
          nextMm = 0;
          nextHh += 1;
        }
        const newTime = `${nextHh.toString().padStart(2, '0')}:${nextMm.toString().padStart(2, '0')}`;
        newData.push({
          time: newTime,
          vol: Math.floor(Math.random() * 5000) + 1000
        });
        return newData;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Mock stats for now
  const currentData = {
    stats: [
      { title: 'volume', val: '45.2K', change: '+12.5%', isUp: true },
      { title: 'keywords', val: '1,204', change: '+5.2%', isUp: true },
      { title: 'engagement', val: '8.4M', change: '-2.1%', isUp: false },
    ],
    trends: trends.map((t, index) => ({
      rank: (index + 1).toString().padStart(2, '0'),
      topic: t.topic_name,
      desc: t.top_keywords.join(', '),
      lang: t.language.toUpperCase(),
      vol: `${Math.floor(t.score)}`,
      momentum: '+50%', // Mock momentum
      trend: 'up'
    }))
  };

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 md:gap-0 mb-6 w-full">
        <div>
          <h1 className="text-3xl font-extrabold text-brand-primary dark:text-white mb-2">{t('trends')}</h1>
          <p className="text-slate-500 dark:text-slate-200">Monitoring real-time cross-linguistic activity.</p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-200 uppercase tracking-widest">
            <div className="w-2 h-2 rounded-full bg-brand-secondary animate-pulse"></div>
            Live Updates Active
          </div>
          <DateFilter />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {currentData.stats.map((stat, idx) => (
          <div key={idx} className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-500 dark:text-slate-200 uppercase tracking-widest mb-1">{t(stat.title)}</h3>
            <div className="flex items-end justify-between">
              <span className="text-3xl font-bold text-brand-primary dark:text-white">{stat.val}</span>
              <div className={`flex items-center gap-1 text-sm font-bold ${stat.isUp ? 'text-brand-secondary' : 'text-red-500'}`}>
                {stat.isUp ? <TrendingUp size={16} /> : <ArrowDown size={16} />}
                {stat.change}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5">
          <h2 className="text-lg font-bold text-brand-primary dark:text-white mb-4">Live Engagement Volume</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="time" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#F8FAFC', borderRadius: '8px' }} 
                  itemStyle={{ color: '#0EA5E9' }}
                />
                <Line type="monotone" dataKey="vol" stroke="#0EA5E9" strokeWidth={3} dot={{ r: 4, fill: '#1E3A8A' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="lg:col-span-1 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5">
          <h2 className="text-lg font-bold text-brand-primary dark:text-white mb-4">Language Distribution</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={LANG_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {LANG_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36}/>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-xl p-5 pb-2 transition-colors duration-300 w-full overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 sm:gap-0">
          <h2 className="text-lg font-bold text-brand-primary dark:text-slate-100">{t('trends') || 'Top Trending Topics'}</h2>
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
        
        <div className="overflow-x-auto w-full">
          <div className="min-w-[700px] w-full">
            <div className="grid grid-cols-12 text-[10px] font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 pb-3 px-2">
              <div className="col-span-1 border-r border-slate-100 dark:border-slate-800">RANK</div>
          <div className="col-span-6 pl-4">TOPIC ENTITY</div>
          <div className="col-span-1 text-center border-x border-slate-100">LANG</div>
          <div className="col-span-2 text-center border-r border-slate-100">{t('volume') || 'VOLUME'}</div>
          <div className="col-span-2 text-right">MOMENTUM</div>
        </div>

        <div className="flex flex-col">
          {currentData.trends.filter(t => filter === 'ALL' || t.lang === (filter === 'ENGLISH' ? 'EN' : 'SO')).map((t, idx) => (
            <div key={idx} className="grid grid-cols-12 items-center py-3 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors px-2 rounded-xl">
              <div className="col-span-1 border-r border-slate-100 dark:border-slate-800 text-3xl font-light text-slate-300 dark:text-slate-700">{t.rank}</div>
              <div className="col-span-6 pl-4 pr-12">
                <div className="text-[15px] font-bold text-brand-primary dark:text-slate-200">{t.topic}</div>
                <div className="text-xs text-slate-400 dark:text-slate-300 mt-0.5">{t.desc}</div>
              </div>
              <div className="col-span-1 text-center border-x border-slate-100 dark:border-slate-800 flex justify-center">
                <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/30 dark:text-brand-secondary text-[10px] font-bold px-2 py-1 rounded-sm">{t.lang}</span>
              </div>
              <div className="col-span-2 text-center border-r border-slate-100 dark:border-slate-800 flex flex-col">
                <span className="text-[13px] font-bold text-slate-800 dark:text-slate-300">{t.vol}</span>
                <span className="text-[10px] text-slate-400 dark:text-slate-300">Tweets</span>
              </div>
              <div className="col-span-2 flex items-center justify-end gap-1 font-bold text-[13px]">
                {t.trend === 'up' ? <TrendingUp size={16} className="text-brand-secondary"/> : <ArrowRight size={16} className="text-slate-400 dark:text-slate-300"/>}
                <span className={t.trend === 'up' ? 'text-brand-secondary' : 'text-slate-400 dark:text-slate-300'}>{t.momentum}</span>
              </div>
            </div>
          ))}
         </div>
        </div>
       </div>
      </div>
    </div>
  )
}

export default Dashboard
