import React, { useState, useEffect } from 'react'
import { useDateRange } from '../contexts/DateRangeContext'
import DateFilter from '../components/DateFilter'
import { useLanguage } from '../contexts/LanguageContext'
import { useTheme } from '../contexts/ThemeContext'
import { getTrends, getModelComparison, getModelHistory } from '../services/api'
import { rangeToQueryParams } from '../utils/dateRange'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, Legend
} from 'recharts'


const Comparison = () => {
  const { range, customDates } = useDateRange()
  const { t } = useLanguage()
  const { isDarkMode } = useTheme()
  
  const [enTrends, setEnTrends] = useState([])
  const [soTrends, setSoTrends] = useState([])
  const [modelComparison, setModelComparison] = useState(null)
  const [modelHistory, setModelHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchComparisonData = async () => {
      setLoading(true)
      try {
        const dateParams = rangeToQueryParams(range, customDates)
        const [enData, soData, comparisonData, historyData] = await Promise.all([
          getTrends('en', dateParams),
          getTrends('so', dateParams),
          getModelComparison().catch(() => null),
          getModelHistory(20, dateParams).catch(() => []),
        ])
        setEnTrends(enData || [])
        setSoTrends(soData || [])
        setModelComparison(comparisonData)
        setModelHistory((historyData || []).slice().reverse())
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
          <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white mb-2 tracking-tight">{t('comparison')}</h1>
        </div>
        <div className="flex flex-col items-end gap-3">
          <DateFilter />
        </div>
      </div>



      {/* Model Evolution Chart */}
      {modelHistory.length > 0 && (() => {
        const chartData = modelHistory.map((r, i) => ({ ...r, run: i + 1 }))
        const latest = chartData.at(-1)
        const fmt = (v) => v != null ? Number(v).toFixed(4) : 'N/A'
        const METRIC_LABELS = { c_v_en: 'C_v EN', c_v_so: 'C_v SO' }
        return (
          <div className="mb-8 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
              <div>
                <h2 className="text-lg font-bold text-brand-primary dark:text-white">BERTopic Quality Metrics</h2>
                <p className="text-sm text-slate-400 mt-0.5">across {modelHistory.length} training runs</p>
              </div>
              <div className="flex flex-wrap gap-4 text-sm font-semibold">
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-brand-primary inline-block rounded" />C_v EN</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-brand-secondary inline-block rounded" />C_v SO</span>
              </div>
            </div>
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 20, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} />
                  <XAxis dataKey="run" tickFormatter={(v) => `Run ${v}`} fontSize={12} tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 1]} fontSize={12} tick={{ fill: '#94a3b8' }} tickLine={false} axisLine={false} tickFormatter={(v) => v.toFixed(2)} />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: isDarkMode ? 'rgba(30, 41, 59, 0.85)' : 'rgba(15, 23, 42, 0.85)',
                      border: isDarkMode ? '1px solid #334155' : 'none',
                      borderRadius: '10px',
                      color: '#f8fafc',
                      padding: '10px 14px',
                    }}
                    itemStyle={{ fontSize: '13px', fontWeight: 'bold', color: '#f8fafc' }}
                    labelFormatter={(v) => `Run ${v} — ${new Date(chartData[v - 1]?.trained_at).toLocaleDateString()}`}
                    formatter={(value, name) => [value != null ? Number(value).toFixed(4) : 'N/A', METRIC_LABELS[name] || name]}
                  />
                  <Line type="monotone" dataKey="c_v_en" stroke="#1E3A8A" strokeWidth={2.5} dot={{ r: 4, fill: '#1E3A8A', strokeWidth: 0 }} activeDot={{ r: 6 }} connectNulls />
                  <Line type="monotone" dataKey="c_v_so" stroke="#0EA5E9" strokeWidth={2.5} dot={{ r: 4, fill: '#0EA5E9', strokeWidth: 0 }} activeDot={{ r: 6 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Latest run summary */}
            <div className="grid grid-cols-2 divide-x divide-slate-100 dark:divide-slate-800 mt-5 pt-4 border-t border-slate-100 dark:border-slate-800">
              {[
                { label: 'C_v EN', value: fmt(latest?.c_v_en), color: 'text-brand-primary dark:text-white' },
                { label: 'C_v SO', value: fmt(latest?.c_v_so), color: 'text-brand-secondary' },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex flex-col items-center py-3">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                  <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>
        )
      })()}

      {modelComparison && (modelComparison.lda_metrics || modelComparison.nmf_metrics || modelComparison.bertopic_metrics) && (
        <div className="mb-10 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-3 pr-6">Model</th>
                  <th className="py-3 pr-6">Language</th>
                  <th className="py-3 pr-6 text-right">C_v</th>
                  <th className="py-3 pr-6 text-right">U_Mass</th>
                  <th className="py-3 pr-6 text-right">Diversity</th>
                  <th className="py-3 text-right">K</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { key: 'lda', label: 'LDA' },
                  { key: 'nmf', label: 'NMF' },
                  { key: 'bertopic', label: 'BERTopic' },
                ].flatMap(({ key, label }) => {
                  const metrics = modelComparison[`${key}_metrics`];
                  const isWinner = modelComparison.selected_deployment_model === key;
                  return ['en', 'so'].map((lang, langIdx) => {
                    const row = metrics?.[lang];
                    const fmt = (v) => (v == null ? 'N/A' : v.toFixed(4));
                    return (
                      <tr
                        key={`${key}-${lang}`}
                        className={`border-b border-slate-100 dark:border-slate-800 ${isWinner ? 'bg-brand-secondary/5 dark:bg-brand-secondary/10' : ''}`}
                      >
                        <td className="py-3 pr-6 font-semibold text-base text-brand-primary dark:text-slate-200">
                          {langIdx === 0 && (
                            <span className="flex items-center gap-1">
                              {isWinner && <span className="text-brand-secondary">&#9733;</span>}
                              {label}
                            </span>
                          )}
                        </td>
                        <td className="py-3 pr-6 text-sm text-slate-500 dark:text-slate-400">{lang === 'en' ? 'English' : 'Somali'}</td>
                        <td className={`py-3 pr-6 text-right font-mono text-sm ${isWinner ? 'text-brand-secondary font-semibold' : 'text-slate-600 dark:text-slate-400'}`}>
                          {fmt(row?.c_v)}
                        </td>
                        <td className="py-3 pr-6 text-right font-mono text-sm text-slate-600 dark:text-slate-400">{fmt(row?.u_mass)}</td>
                        <td className="py-3 pr-6 text-right font-mono text-sm text-slate-600 dark:text-slate-400">{fmt(row?.diversity)}</td>
                        <td className="py-3 text-right font-mono text-sm text-slate-500 dark:text-slate-400">{row?.K ?? 'N/A'}</td>
                      </tr>
                    );
                  });
                })}
              </tbody>
            </table>
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
              <span className="bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/20 dark:text-brand-secondary text-xs font-semibold px-3 py-1 rounded-sm">REGION: WORLDWIDE</span>
            </div>

            <div className="space-y-6 relative border-l-2 border-slate-100 dark:border-slate-800 pl-8">
              {enTrends.length === 0 ? <p className="text-sm text-slate-500">No English topics tracked yet.</p> : null}
              {enTrends.map((t, idx) => (
                <div key={idx} className="flex justify-between items-center group cursor-default">
                  <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                    {String(idx + 1).padStart(2, '0')}
                  </div>
                  <div className="flex-1 pr-6">
                    <h3 className="text-base font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.label || t.topic_name}</h3>
                    <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500 dark:text-slate-300">
                       <span>Score: <span className="text-slate-700 dark:text-slate-200 font-mono">{t.score ? t.score.toFixed(1) : 0}</span></span>
                       <span>Keywords: <span className="text-brand-primary dark:text-slate-200">{t.top_keywords?.join(', ')}</span></span>
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
              <span className="bg-brand-primary/5 text-brand-primary dark:bg-brand-secondary/20 dark:text-brand-secondary text-xs font-semibold px-3 py-1 rounded-sm">REGION: EAST AFRICA</span>
            </div>

            <div className="space-y-6 relative border-l-2 border-slate-100 dark:border-slate-800 pl-8">
              {soTrends.length === 0 ? <p className="text-sm text-slate-500">No Somali topics tracked yet.</p> : null}
              {soTrends.map((t, idx) => (
                 <div key={idx} className="flex justify-between items-center group cursor-default">
                   <div className="absolute left-[-26px] transform -translate-x-1/2 text-4xl font-extralight text-brand-primary/20 dark:text-slate-800 group-hover:text-brand-secondary transition-colors -z-10 bg-white dark:bg-slate-900 px-2 py-4">
                     {String(idx + 1).padStart(2, '0')}
                   </div>
                   <div className="flex-1 pr-6">
                     <h3 className="text-base font-bold text-brand-primary dark:text-slate-200 group-hover:text-brand-secondary transition-colors mb-2">{t.label || t.topic_name}</h3>
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
