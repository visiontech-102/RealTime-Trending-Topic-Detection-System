import React from 'react'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { Activity, Database, GitMerge, FileCode2 } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'

const MOCK_COMPARISON_DATA = {
  '24 HOURS': {
    stats: {
      db: "12.4M Tweets Processed",
      nlp: "9.8M Tokens Cleaned",
      coh: "0.81",
      sentiment: "Live Sentiment Active"
    },
    en: [
      { rank: '01', topic: 'Generative AI Governance', vol: '1.2M', momentum: '+14.2%', coherence: '0.84', sentiment: 'MIXED', trend: 'up', sparks: "M 0 10 Q 5 20 10 15 T 40 5" },
      { rank: '02', topic: 'Renewable Grid Parity', vol: '840K', momentum: '+8.5%', coherence: '0.79', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 15 Q 10 5 20 10 T 40 0" },
      { rank: '03', topic: 'Remote Work Legislation', vol: '612K', momentum: 'STABLE', coherence: '0.72', sentiment: 'NEUTRAL', trend: 'flat', sparks: "M 0 10 L 40 10" },
      { rank: '04', topic: 'Sustainable Supply Chains', vol: '450K', momentum: '+2.1%', coherence: '0.81', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 20 Q 10 10 20 15 T 40 5" },
    ],
    so: [
      { rank: '01', topic: 'Abaaraha iyo Gurmadka (Droughts)', vol: '92K', momentum: '+42.8%', coherence: '0.91', sentiment: 'NEGATIVE', trend: 'up', sparks: "M 0 20 Q 5 15 15 25 T 40 0" },
      { rank: '02', topic: 'Doorashooyinka 2024 (Elections)', vol: '78K', momentum: '+18.1%', coherence: '0.85', sentiment: 'MIXED', trend: 'up', sparks: "M 0 15 Q 10 20 25 10 T 40 5" },
      { rank: '03', topic: 'Maalgashiga Dekedaha (Port Investments)', vol: '55K', momentum: '+4.3%', coherence: '0.76', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 10 Q 15 15 25 10 T 40 5" },
      { rank: '04', topic: 'Horumarka Tiknoolajiyada (Tech Dev)', vol: '31K', momentum: 'STABLE', coherence: '0.68', sentiment: 'NEUTRAL', trend: 'flat', sparks: "M 0 10 L 40 10" },
    ]
  },
  '7 DAYS': {
    stats: {
      db: "85.2M Tweets Processed",
      nlp: "68.4M Tokens Cleaned",
      coh: "0.85",
      sentiment: "Historical Sentiment Applied"
    },
    en: [
      { rank: '01', topic: 'Global Summit 2024', vol: '8.4M', momentum: '+54.2%', coherence: '0.88', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 25 Q 10 5 20 15 T 40 5" },
      { rank: '02', topic: 'Tech AI Updates', vol: '5.2M', momentum: '+12.5%', coherence: '0.82', sentiment: 'MIXED', trend: 'up', sparks: "M 0 10 Q 15 20 25 5 T 40 10" },
      { rank: '03', topic: 'Market Volatility', vol: '4.1M', momentum: '-5.4%', coherence: '0.75', sentiment: 'NEGATIVE', trend: 'down', sparks: "M 0 5 Q 10 20 20 15 T 40 25" },
      { rank: '04', topic: 'Crypto Regulations', vol: '2.8M', momentum: 'STABLE', coherence: '0.78', sentiment: 'NEUTRAL', trend: 'flat', sparks: "M 0 15 L 40 15" },
    ],
    so: [
      { rank: '01', topic: 'Kheyre 2024 Ololaha', vol: '540K', momentum: '+88.1%', coherence: '0.94', sentiment: 'MIXED', trend: 'up', sparks: "M 0 20 Q 10 5 20 15 T 40 0" },
      { rank: '02', topic: 'Isbedelka Cimilada', vol: '320K', momentum: '+24.5%', coherence: '0.88', sentiment: 'NEGATIVE', trend: 'up', sparks: "M 0 15 Q 10 25 20 10 T 40 5" },
      { rank: '03', topic: 'Ganacsiga Geeska Afrika', vol: '210K', momentum: '+12.3%', coherence: '0.81', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 10 Q 15 15 25 5 T 40 10" },
      { rank: '04', topic: 'Puntland Deegaanada', vol: '150K', momentum: '-2.1%', coherence: '0.74', sentiment: 'NEUTRAL', trend: 'down', sparks: "M 0 5 Q 15 10 25 20 T 40 20" },
    ]
  },
  '30 DAYS': {
    stats: {
      db: "340.8M Tweets Processed",
      nlp: "275.1M Tokens Cleaned",
      coh: "0.89",
      sentiment: "Macro Sentiment Active"
    },
    en: [
      { rank: '01', topic: 'Climate Action Protocols', vol: '32.1M', momentum: '+120.4%', coherence: '0.92', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 25 Q 15 5 25 15 T 40 0" },
      { rank: '02', topic: 'Interest Rate Decisions', vol: '28.5M', momentum: '+85.2%', coherence: '0.86', sentiment: 'NEGATIVE', trend: 'up', sparks: "M 0 20 Q 10 15 20 25 T 40 5" },
      { rank: '03', topic: 'Electric Vehicle Surge', vol: '18.4M', momentum: '+42.1%', coherence: '0.81', sentiment: 'MIXED', trend: 'up', sparks: "M 0 15 Q 10 5 25 15 T 40 10" },
      { rank: '04', topic: 'Global Health Initiatives', vol: '12.8M', momentum: '+15.4%', coherence: '0.78', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 10 Q 15 20 25 10 T 40 5" },
    ],
    so: [
      { rank: '01', topic: 'Arrimaha Federaalka', vol: '2.4M', momentum: '+142.5%', coherence: '0.95', sentiment: 'MIXED', trend: 'up', sparks: "M 0 25 Q 10 10 25 20 T 40 5" },
      { rank: '02', topic: 'Qaxootiga iyo Barakacayaasha', vol: '1.8M', momentum: '+75.8%', coherence: '0.91', sentiment: 'NEGATIVE', trend: 'up', sparks: "M 0 20 Q 15 25 25 10 T 40 5" },
      { rank: '03', topic: 'Tijaabada Shidaalka', vol: '950K', momentum: '+54.2%', coherence: '0.85', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 15 Q 10 5 25 15 T 40 10" },
      { rank: '04', topic: 'Waxbarashada Casriga', vol: '820K', momentum: '+28.4%', coherence: '0.82', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 10 Q 15 15 25 5 T 40 10" },
    ]
  },
  'CUSTOM RANGE': {
    stats: {
      db: "1.2B Tweets Processed",
      nlp: "980.5M Tokens Cleaned",
      coh: "0.92",
      sentiment: "Historical Sentiment Applied"
    },
    en: [
      { rank: '01', topic: 'Geopolitical Shifts 2023', vol: '145.2M', momentum: 'STABLE', coherence: '0.95', sentiment: 'MIXED', trend: 'flat', sparks: "M 0 15 L 40 15" },
      { rank: '02', topic: 'Pandemic Recovery Economy', vol: '98.4M', momentum: '+15.2%', coherence: '0.88', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 20 Q 10 10 25 15 T 40 5" },
      { rank: '03', topic: 'Space Exploration Milestones', vol: '65.8M', momentum: '+42.8%', coherence: '0.84', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 25 Q 15 5 25 10 T 40 0" },
      { rank: '04', topic: 'Supply Chain Bottlenecks', vol: '42.1M', momentum: '-18.4%', coherence: '0.79', sentiment: 'NEGATIVE', trend: 'down', sparks: "M 0 5 Q 15 15 25 25 T 40 15" },
    ],
    so: [
      { rank: '01', topic: 'Taariikhda Qaranimada', vol: '12.5M', momentum: 'STABLE', coherence: '0.96', sentiment: 'POSITIVE', trend: 'flat', sparks: "M 0 15 L 40 15" },
      { rank: '02', topic: 'Dib u eegis Dastuurka', vol: '8.4M', momentum: '+35.4%', coherence: '0.92', sentiment: 'MIXED', trend: 'up', sparks: "M 0 20 Q 10 5 25 15 T 40 10" },
      { rank: '03', topic: 'Horumarinta Beeraha', vol: '5.2M', momentum: '+22.1%', coherence: '0.87', sentiment: 'POSITIVE', trend: 'up', sparks: "M 0 15 Q 15 20 25 10 T 40 5" },
      { rank: '04', topic: 'Amniga Gacanka Cadan', vol: '3.8M', momentum: '-8.5%', coherence: '0.83', sentiment: 'NEGATIVE', trend: 'down', sparks: "M 0 5 Q 10 15 25 10 T 40 20" },
    ]
  }
};

const Sparkline = ({ pathD, trend }) => (
  <svg width="40" height="25" viewBox="0 0 40 25" className="overflow-visible">
    <path 
      d={pathD} 
      fill="none" 
      stroke={trend === 'up' ? '#0ea5e9' : '#94a3b8'} // using brand-secondary approx visually
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round" 
    />
  </svg>
)

const MethodologyCard = ({ icon: Icon, title, desc, stat }) => (
  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm flex items-start gap-4">
    <div className="p-3 bg-brand-secondary/10 text-brand-secondary rounded-lg">
       <Icon size={20} />
    </div>
    <div>
      <h4 className="text-[10px] font-extrabold text-brand-primary dark:text-slate-400 uppercase tracking-widest mb-1">{title}</h4>
      <p className="text-xs text-slate-500 dark:text-slate-300 mb-2 leading-relaxed">{desc}</p>
      <div className="text-sm font-bold text-brand-primary dark:text-white font-mono">{stat}</div>
    </div>
  </div>
)

const Comparison = () => {
  const { range } = useDateRange()
  const { t } = useLanguage()
  const currentData = MOCK_COMPARISON_DATA[range] || MOCK_COMPARISON_DATA['24 HOURS'];

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h2 className="text-[10px] font-extrabold text-brand-secondary uppercase tracking-widest mb-2 flex items-center gap-2">
            <Activity size={12} /> BERTopic & LDA MODELLING PIPELINE
          </h2>
          <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white mb-2 tracking-tight">{t('comparison')}</h1>
          <p className="text-sm text-brand-primary/70 dark:text-slate-200">Applying unsupervised topic modeling (Methodology Ch 3) to analyze divergent semantic clusters.</p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-2 text-[10px] font-extrabold text-slate-500 dark:text-slate-200 uppercase tracking-widest">
             PIPELINE ACTIVE: STREAMING <div className="w-2 h-2 rounded-full bg-brand-secondary ml-1 animate-pulse"></div>
          </div>
          <DateFilter />
        </div>
      </div>

      {/* Methodology Dashboard Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 lg:mb-12">
        <MethodologyCard 
          icon={Database} 
          title="Data Ingestion" 
          desc="Real-time X (Twitter) API streaming with English & Somali lexicons." 
          stat={currentData.stats.db} 
        />
        <MethodologyCard 
          icon={FileCode2} 
          title="NLP Preprocessing" 
          desc="Tokenization, noise removal, and bilingual stop-word elimination." 
          stat={currentData.stats.nlp} 
        />
        <MethodologyCard 
          icon={GitMerge} 
          title="Topic Modeling" 
          desc="BERTopic and LDA semantic clustering with feature representation." 
          stat={`Avg Coherence: ${currentData.stats.coh}`} 
        />
        <MethodologyCard 
          icon={Activity} 
          title="VADER Sentiment" 
          desc="Real-time sentiment burst detection tracking positivity variance." 
          stat={currentData.stats.sentiment} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
        {/* English Column */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">
            <h2 className="text-xl font-bold text-brand-primary dark:text-white tracking-tight">English (Global)</h2>
            <span className="bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/20 dark:text-brand-secondary text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-sm">REGION: WORLDWIDE</span>
          </div>

          <div className="space-y-6 relative border-l-2 border-slate-100 dark:border-slate-800 pl-8">
            {currentData.en.map((t, idx) => (
              <div key={idx} className="flex justify-between items-center group cursor-default">
                <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                  {t.rank}
                </div>
                <div className="flex-1 pr-6">
                  <h3 className="text-[15px] font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.topic}</h3>
                  <div className="flex flex-wrap gap-x-4 gap-y-2 text-[9px] uppercase font-bold tracking-widest text-slate-400 dark:text-slate-300">
                     <span>VOL: <span className="text-slate-600 dark:text-slate-200 font-mono">{t.vol}</span></span>
                     <span className="flex items-center gap-1">
                       GROWTH: <span className={t.trend === 'up' ? 'text-brand-secondary' : 'text-slate-500'}>{t.momentum}</span>
                     </span>
                     <span>LDA COH: <span className="text-brand-primary dark:text-slate-200 font-mono">{t.coherence}</span></span>
                     <span className={`px-1.5 rounded-sm ${t.sentiment === 'POSITIVE' ? 'bg-brand-secondary/20 text-brand-secondary' : t.sentiment === 'NEGATIVE' ? 'bg-red-500/20 text-red-500' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'}`}>
                       {t.sentiment}
                     </span>
                  </div>
                </div>
                <div className="pl-4 border-l border-slate-100 dark:border-slate-800 hidden sm:block">
                  <Sparkline pathD={t.sparks} trend={t.trend} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Somali Column */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">
            <h2 className="text-xl font-bold text-brand-primary dark:text-white tracking-tight">Af-Soomaali (Regional)</h2>
            <span className="bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/20 dark:text-brand-secondary text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-sm">REGION: EAST AFRICA</span>
          </div>

          <div className="space-y-6 relative border-l-2 border-slate-100 dark:border-slate-800 pl-8">
            {currentData.so.map((t, idx) => (
               <div key={idx} className="flex justify-between items-center group cursor-default">
                 <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                   {t.rank}
                 </div>
                 <div className="flex-1 pr-6">
                   <h3 className="text-[15px] font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.topic}</h3>
                   <div className="flex flex-wrap gap-x-4 gap-y-2 text-[9px] uppercase font-bold tracking-widest text-slate-400 dark:text-slate-300">
                      <span>VOL: <span className="text-slate-600 dark:text-slate-200 font-mono">{t.vol}</span></span>
                      <span className="flex items-center gap-1">
                        GROWTH: <span className={t.trend === 'up' ? 'text-brand-secondary' : 'text-slate-500'}>{t.momentum}</span>
                      </span>
                      <span>LDA COH: <span className="text-brand-primary dark:text-slate-200 font-mono">{t.coherence}</span></span>
                      <span className={`px-1.5 rounded-sm ${t.sentiment === 'POSITIVE' ? 'bg-brand-secondary/20 text-brand-secondary' : t.sentiment === 'NEGATIVE' ? 'bg-red-500/20 text-red-500' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'}`}>
                        {t.sentiment}
                      </span>
                   </div>
                 </div>
                 <div className="pl-4 border-l border-slate-100 dark:border-slate-800 hidden sm:block">
                   <Sparkline pathD={t.sparks} trend={t.trend} />
                 </div>
               </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Comparison
