import React, { useState, useEffect } from 'react'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { Activity } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { getTrends, getModelComparison } from '../services/api'
import { rangeToQueryParams } from '../utils/dateRange'


const Comparison = () => {
  const { range, customDates } = useDateRange()
  const { t } = useLanguage()
  
  const [enTrends, setEnTrends] = useState([])
  const [soTrends, setSoTrends] = useState([])
  const [modelComparison, setModelComparison] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchComparisonData = async () => {
      setLoading(true)
      try {
        const dateParams = rangeToQueryParams(range, customDates)
        const [enData, soData, comparisonData] = await Promise.all([
          getTrends('en', dateParams),
          getTrends('so', dateParams),
          getModelComparison().catch(() => null),
        ])
        setEnTrends(enData || [])
        setSoTrends(soData || [])
        setModelComparison(comparisonData)
      } catch (err) {
        console.error("Failed to fetch comparison:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchComparisonData()
  }, [range, customDates])

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h2 className="text-[10px] font-extrabold text-brand-secondary uppercase tracking-widest mb-2 flex items-center gap-2">
            <Activity size={12} /> BERTopic MULTILINGUAL MODELLING PIPELINE
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



      {modelComparison?.criteria_comparison?.length > 0 && (
        <div className="mb-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-bold text-brand-primary dark:text-white mb-1">
            LDA vs BERTopic — Deployment Selection
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Selected for production: <span className="font-bold text-brand-secondary uppercase">{modelComparison.selected_deployment_model}</span>
            {' '}({modelComparison.criteria_winner_count?.bertopic ?? 0}/{modelComparison.criteria_comparison.length} criteria)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-[10px] uppercase tracking-widest text-slate-500">
                  <th className="py-2 pr-4">Criterion</th>
                  <th className="py-2 pr-4">LDA (Baseline)</th>
                  <th className="py-2 pr-4">BERTopic</th>
                  <th className="py-2">Winner</th>
                </tr>
              </thead>
              <tbody>
                {modelComparison.criteria_comparison.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 pr-4 font-semibold text-brand-primary dark:text-slate-200">{row.criterion}</td>
                    <td className="py-2 pr-4 text-slate-600 dark:text-slate-400 max-w-xs">{row.lda}</td>
                    <td className="py-2 pr-4 text-slate-600 dark:text-slate-400 max-w-xs">{row.bertopic}</td>
                    <td className="py-2 font-mono uppercase text-brand-secondary">{row.deployment_winner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex gap-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">
            <a href="http://localhost:8000/visualizations/lda" target="_blank" rel="noreferrer" className="hover:text-brand-secondary">pyLDAvis →</a>
            <a href="http://localhost:8000/visualizations/bertopic" target="_blank" rel="noreferrer" className="hover:text-brand-secondary">BERTopic intertopic →</a>
          </div>
        </div>
      )}

      {loading ? (
        <div className="py-10 text-center text-slate-500 dark:text-slate-400 font-bold">Loading cross-lingual clusters...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
          {/* English Column */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 shadow-sm">
            <div className="flex justify-between items-center mb-8 border-b border-slate-100 dark:border-slate-800 pb-4">
              <h2 className="text-xl font-bold text-brand-primary dark:text-white tracking-tight">English (Global)</h2>
              <span className="bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/20 dark:text-brand-secondary text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-sm">REGION: WORLDWIDE</span>
            </div>

            <div className="space-y-6 relative border-l-2 border-slate-100 dark:border-slate-800 pl-8">
              {enTrends.length === 0 ? <p className="text-sm text-slate-500">No English topics tracked yet.</p> : null}
              {enTrends.map((t, idx) => (
                <div key={idx} className="flex justify-between items-center group cursor-default">
                  <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                    {String(idx + 1).padStart(2, '0')}
                  </div>
                  <div className="flex-1 pr-6">
                    <h3 className="text-[15px] font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.topic_name}</h3>
                    <div className="flex flex-wrap gap-x-4 gap-y-2 text-[9px] uppercase font-bold tracking-widest text-slate-400 dark:text-slate-300">
                       <span>SCORE: <span className="text-slate-600 dark:text-slate-200 font-mono">{t.score ? t.score.toFixed(1) : 0}</span></span>
                       <span>KEYWORDS: <span className="text-brand-primary dark:text-slate-200">{t.top_keywords?.join(', ')}</span></span>
                    </div>
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
              {soTrends.length === 0 ? <p className="text-sm text-slate-500">No Somali topics tracked yet.</p> : null}
              {soTrends.map((t, idx) => (
                 <div key={idx} className="flex justify-between items-center group cursor-default">
                   <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                     {String(idx + 1).padStart(2, '0')}
                   </div>
                   <div className="flex-1 pr-6">
                     <h3 className="text-[15px] font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.topic_name}</h3>
                     <div className="flex flex-wrap gap-x-4 gap-y-2 text-[9px] uppercase font-bold tracking-widest text-slate-400 dark:text-slate-300">
                        <span>SCORE: <span className="text-slate-600 dark:text-slate-200 font-mono">{t.score ? t.score.toFixed(1) : 0}</span></span>
                        <span>KEYWORDS: <span className="text-brand-primary dark:text-slate-200">{t.top_keywords?.join(', ')}</span></span>
                     </div>
                   </div>
                 </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Comparison
