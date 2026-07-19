import React, { useState, useEffect } from 'react'
import { FileDown, FileText, Loader2 } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { getHistory } from '../services/api'
import { useDateRange } from '../contexts/DateRangeContext'
import { rangeToQueryParams } from '../utils/dateRange'
import DateFilter from '../components/DateFilter'

const PAGE_SIZE = 20

const Export = () => {
  const { range, customDates } = useDateRange()
  const [isExporting, setIsExporting] = useState(false)
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false)
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const { t } = useLanguage()

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      setPage(0)
      try {
        let data = []
        const dateParams = rangeToQueryParams(range, customDates)
        for (const lng of ['en', 'so']) {
          const result = await getHistory(lng, dateParams)
          data = [...data, ...result]
        }
        data.sort((a, b) => b.score - a.score)
        setTrends(data)
      } catch (err) {
        console.error('Error fetching data for export:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [range, customDates])

  const totalPages = Math.ceil(trends.length / PAGE_SIZE)
  const pageData = trends.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const dateRangeLabel = () => {
    if (range === 'custom' && customDates?.startDate && customDates?.endDate) {
      return `${customDates.startDate} → ${customDates.endDate}`
    }
    const labels = { '24h': 'Last 24 Hours', '7d': 'Last 7 Days', '30d': 'Last 30 Days', 'all': 'All Time' }
    return labels[range] || 'Last 24 Hours'
  }

  const handleExportCSV = () => {
    setIsExporting(true)
    setTimeout(() => {
      try {
        const headers = ['Rank', 'Topic Label', 'Keywords', 'Language', 'Score', 'Volume', 'Period']
        const rows = trends.map((row, idx) => [
          String(idx + 1).padStart(2, '0'),
          `"${row.label || row.topic_name || ''}"`,
          `"${row.top_keywords?.join(', ') || ''}"`,
          (row.language || '').toUpperCase(),
          row.score?.toFixed(2) ?? '',
          row.volume ?? '',
          row.tweet_period_to ? new Date(row.tweet_period_to).toISOString().slice(0, 10) : '',
        ])
        const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
        const link = document.createElement('a')
        link.href = 'data:text/csv;charset=utf-8,' + encodeURI(csv)
        link.download = 'VisionTech_Trend_Export.csv'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } catch (err) {
        console.error('CSV export failed', err)
      } finally {
        setIsExporting(false)
      }
    }, 800)
  }

  const handleGeneratePDF = () => {
    setIsGeneratingPDF(true)
    setTimeout(() => {
      try {
        const rows = trends.map((row, idx) => `
          <tr>
            <td>${String(idx + 1).padStart(2, '0')}</td>
            <td>${row.label || row.topic_name || ''}</td>
            <td>${row.top_keywords?.join(', ') || ''}</td>
            <td>${(row.language || '').toUpperCase()}</td>
            <td>${row.score?.toFixed(2) ?? ''}</td>
            <td>${row.volume ?? 'N/A'}</td>
          </tr>`).join('')

        const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
          <title>VisionTech Trend Report</title>
          <style>
            body { font-family: sans-serif; font-size: 12px; padding: 24px; }
            h1 { font-size: 20px; margin-bottom: 4px; }
            p { color: #64748b; margin-bottom: 16px; font-size: 11px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #1E3A8A; color: white; padding: 8px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
            td { padding: 7px 8px; border-bottom: 1px solid #e2e8f0; font-size: 11px; }
            tr:nth-child(even) td { background: #f8fafc; }
            @media print { body { padding: 0; } }
          </style></head><body>
          <h1>VisionTech — Trending Topics Report</h1>
          <p>Generated: ${new Date().toUTCString()} | Range: ${dateRangeLabel()} | Total: ${trends.length} topics</p>
          <table>
            <thead><tr><th>#</th><th>Topic</th><th>Keywords</th><th>Lang</th><th>Score</th><th>Volume</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <script>window.onload = () => window.print()</script>
          </body></html>`

        const win = window.open('', '_blank')
        if (win) {
          win.document.write(html)
          win.document.close()
        }
      } catch (err) {
        console.error('PDF generation failed', err)
      } finally {
        setIsGeneratingPDF(false)
      }
    }, 600)
  }

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
        <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white tracking-tight">{t('export')}</h1>
        <DateFilter />
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-12 gap-6">
        {/* Left Control Panel */}
        <div className="lg:col-span-4 bg-slate-100 dark:bg-slate-800 rounded-sm p-6 lg:p-8 transition-colors w-full">
          <h3 className="text-[11px] font-bold text-brand-primary dark:text-slate-200 uppercase tracking-widest mb-8">CURRENT SELECTION</h3>

          <div className="mb-8">
            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-2">TOTAL RECORDS</div>
            <div className="text-3xl font-light text-brand-primary dark:text-slate-100">
              {loading ? <Loader2 size={24} className="animate-spin text-slate-400" /> : trends.length.toLocaleString()}
            </div>
          </div>

          <div className="mb-8">
            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-2">DATE RANGE</div>
            <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{dateRangeLabel()}</div>
          </div>

          <div className="mb-10">
            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-3">LANGUAGES INCLUDED</div>
            <div className="flex gap-2">
              {(() => {
                const enCount = trends.filter(r => r.language === 'en').length
                const soCount = trends.filter(r => r.language === 'so').length
                return (
                  <>
                    {enCount > 0 && (
                      <span className="bg-brand-primary text-white text-[9px] font-extrabold uppercase px-3 py-1 rounded-sm tracking-wider">
                        ENGLISH ({enCount})
                      </span>
                    )}
                    {soCount > 0 && (
                      <span className="bg-brand-secondary text-white text-[9px] font-extrabold uppercase px-3 py-1 rounded-sm tracking-wider">
                        SOMALI ({soCount})
                      </span>
                    )}
                    {enCount === 0 && soCount === 0 && (
                      <span className="text-slate-400 text-[9px] italic">No data</span>
                    )}
                  </>
                )
              })()}
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={handleExportCSV}
              disabled={isExporting || loading || trends.length === 0}
              className={`w-full text-white py-4 rounded-sm transition-colors text-[11px] font-extrabold uppercase tracking-widest flex justify-center items-center gap-2 ${
                (isExporting || loading || trends.length === 0)
                  ? 'bg-slate-400 cursor-not-allowed'
                  : 'bg-brand-primary hover:bg-brand-secondary'
              }`}
            >
              {isExporting ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />}
              {isExporting ? 'GENERATING CSV...' : 'EXPORT TO CSV'}
            </button>
            <button
              onClick={handleGeneratePDF}
              disabled={isGeneratingPDF || loading || trends.length === 0}
              className={`w-full py-4 rounded-sm transition-colors text-[11px] font-bold uppercase tracking-wider flex justify-center items-center gap-2 shadow-sm ${
                (isGeneratingPDF || loading || trends.length === 0)
                  ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed border border-transparent'
                  : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-brand-secondary hover:text-brand-secondary text-brand-primary dark:text-slate-200'
              }`}
            >
              {isGeneratingPDF ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
              {isGeneratingPDF ? 'GENERATING PDF...' : 'GENERATE PDF REPORT'}
            </button>
          </div>
        </div>

        {/* Right Preview Table */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm rounded-sm p-0 transition-colors w-full overflow-hidden flex flex-col">
          <div className="overflow-x-auto w-full flex-1">
            <div className="min-w-[600px]">
              <div className="grid grid-cols-12 text-[10px] bg-slate-50 dark:bg-slate-900 font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 p-4">
                <div className="col-span-1 text-center">#</div>
                <div className="col-span-5">TOPIC</div>
                <div className="col-span-1 text-center">LANG</div>
                <div className="col-span-2 text-center">SCORE</div>
                <div className="col-span-3 text-center">VOLUME</div>
              </div>

              <div className="flex flex-col border-b border-slate-100 dark:border-slate-800">
                {loading ? (
                  <div className="p-10 text-center text-slate-500 flex justify-center items-center gap-2">
                    <Loader2 size={16} className="animate-spin" /> Loading...
                  </div>
                ) : trends.length === 0 ? (
                  <div className="p-10 text-center text-slate-500 dark:text-slate-400 text-xs italic">No data available to export.</div>
                ) : pageData.map((row, idx) => (
                  <div
                    key={row._id || idx}
                    className="grid grid-cols-12 items-center p-4 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    <div className="col-span-1 text-center text-2xl font-extralight text-brand-primary/30 dark:text-slate-700">
                      {String(page * PAGE_SIZE + idx + 1).padStart(2, '0')}
                    </div>
                    <div className="col-span-5 pr-4">
                      <div className="text-[13px] font-bold text-brand-primary dark:text-slate-200 mb-0.5">{row.label || row.topic_name}</div>
                      <div className="text-[9px] font-bold uppercase tracking-wider text-brand-secondary truncate">{row.top_keywords?.join(', ')}</div>
                    </div>
                    <div className="col-span-1 text-center">
                      <span className="bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/30 dark:text-brand-secondary text-[10px] font-bold px-2 py-0.5 rounded-sm uppercase">
                        {(row.language || '').toUpperCase()}
                      </span>
                    </div>
                    <div className="col-span-2 text-center text-[13px] font-bold text-brand-secondary">
                      {row.score?.toFixed(2) ?? '—'}
                    </div>
                    <div className="col-span-3 text-center font-mono text-[12px] text-slate-700 dark:text-slate-300 font-medium">
                      {row.volume != null ? row.volume.toLocaleString() : '—'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Pagination footer */}
          <div className="p-5 flex justify-between items-center bg-white dark:bg-slate-900 text-xs font-medium text-slate-500 dark:text-slate-400 mt-auto border-t border-slate-100 dark:border-slate-800">
            <div>
              {trends.length > 0
                ? `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, trends.length)} of ${trends.length} records`
                : '0 records'}
            </div>
            <div className="flex gap-4 font-bold text-[10px] uppercase tracking-widest">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className={page === 0 ? 'text-slate-300 dark:text-slate-700 cursor-not-allowed' : 'text-brand-primary dark:text-white hover:text-brand-secondary transition-colors'}
              >
                PREV
              </button>
              <span className="text-slate-400">{totalPages > 0 ? `${page + 1} / ${totalPages}` : '—'}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className={page >= totalPages - 1 ? 'text-slate-300 dark:text-slate-700 cursor-not-allowed' : 'text-brand-primary dark:text-white hover:text-brand-secondary transition-colors'}
              >
                NEXT
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Export
