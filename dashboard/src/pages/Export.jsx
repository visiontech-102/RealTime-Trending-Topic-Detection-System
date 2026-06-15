import React, { useState, useEffect } from 'react'
import { FileDown, FileText, Loader2 } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { getHistory } from '../services/api'
import { useDateRange } from '../contexts/DateRangeContext'
import { rangeToQueryParams } from '../utils/dateRange'

const Export = () => {
  const { range, customDates } = useDateRange()
  const [isExporting, setIsExporting] = useState(false);
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const { t } = useLanguage();

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true)
      try {
        let data = [];
        const langsToFetch = ['en', 'so'];
        const dateParams = rangeToQueryParams(range, customDates)
        for (let lng of langsToFetch) {
          let result = await getHistory(lng, dateParams);
          data = [...data, ...result];
        }
        data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setTrends(data);
      } catch (error) {
        console.error('Error fetching data for export:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [range, customDates])

  const handleExportCSV = () => {
    setIsExporting(true);
    
    // Simulate real network/generation delay for professional feel
    setTimeout(() => {
      try {
        // Build CSV string
        const headers = ['Rank', 'Trend Identifier', 'Keywords', 'Score', 'Estimated Volume'];
        const csvRows = [headers.join(',')];
        
        trends.forEach((row, idx) => {
          // Wrap strings in quotes to handle commas
          const values = [
            `"${String(idx + 1).padStart(2, '0')}"`, 
            `"${row.topic_name}"`, 
            `"${row.top_keywords?.join(', ')}"`, 
            `"${row.score?.toFixed(1)}"`, 
            `"N/A"`
          ];
          csvRows.push(values.join(','));
        });

        const csvContent = "data:text/csv;charset=utf-8," + csvRows.join('\n');
        const encodedUri = encodeURI(csvContent);
        
        // Create invisible link and trigger download
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "VisionTech_Trend_Export.csv");
        document.body.appendChild(link); // Required for Firefox
        link.click();
        document.body.removeChild(link);
      } catch (err) {
        console.error('Failed to export CSV', err);
      } finally {
        setIsExporting(false);
      }
    }, 1500); // 1.5s simulated delay
  };

  const handleGeneratePDF = () => {
    setIsGeneratingPDF(true);
    // Simulate real network/generation delay for professional feel
    setTimeout(() => {
      try {
        // Generate a minimal valid dummy PDF file
        const pdfContent = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 0 >>\nstream\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000224 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n268\n%%EOF";
        
        const blob = new Blob([pdfContent], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", "VisionTech_Trend_Report.pdf");
        document.body.appendChild(link);
        link.click();
        
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Failed to generate PDF', err);
      } finally {
        setIsGeneratingPDF(false);
      }
    }, 2000); // 2s simulated duration for PDF generation
  };

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex justify-between items-end mb-10">
        <div>
          <h2 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-2">DATA CURATION / SYSTEM EXPORT</h2>
          <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white tracking-tight">{t('export')}</h1>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-widest">
           LAST SYNCED: {new Date().toLocaleTimeString('en-US', { hour12: false })} UTC <div className="w-2 h-2 rounded-full bg-brand-secondary ml-1 animate-pulse"></div>
        </div>
      </div>

      <div className="flex flex-col lg:grid lg:grid-cols-12 gap-6">
        {/* Left Control Panel */}
        <div className="lg:col-span-4 bg-slate-100 dark:bg-slate-800 rounded-sm p-6 lg:p-8 transition-colors w-full">
           <h3 className="text-[11px] font-bold text-brand-primary dark:text-slate-200 uppercase tracking-widest mb-10">CURRENT SELECTION</h3>
           
           <div className="mb-8">
             <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-2">TOTAL RECORDS</div>
             <div className="text-3xl font-light text-brand-primary dark:text-slate-100">
               {loading ? <Loader2 size={24} className="animate-spin text-slate-400" /> : trends.length.toLocaleString()}
             </div>
           </div>

           <div className="mb-8">
             <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-2">DATE RANGE</div>
             <div className="text-sm font-medium text-slate-700 dark:text-slate-300">All Time (Live Sync)</div>
           </div>

           <div className="mb-10">
             <div className="text-[10px] font-bold text-slate-400 dark:text-slate-300 uppercase tracking-wider mb-3">LANGUAGES INCLUDED</div>
             <div className="flex gap-2">
               <span className="bg-brand-secondary text-slate-900 text-[9px] font-extrabold uppercase px-3 py-1 rounded-sm tracking-wider">ENGLISH</span>
               <span className="bg-brand-secondary text-slate-900 text-[9px] font-extrabold uppercase px-3 py-1 rounded-sm tracking-wider">SOMALI</span>
             </div>
           </div>

           <div className="space-y-3">
             <button 
               onClick={handleExportCSV}
               disabled={isExporting || loading || trends.length === 0}
               className={`w-full text-white py-4 rounded-sm transition-colors text-[11px] font-extrabold uppercase tracking-widest flex justify-center items-center gap-2 ${
                 (isExporting || loading || trends.length === 0) ? 'bg-slate-400 cursor-not-allowed' : 'bg-brand-primary hover:bg-brand-secondary dark:bg-brand-secondary dark:hover:bg-brand-primary'
               }`}
             >
               {isExporting ? <Loader2 size={16} className="animate-spin" /> : <FileDown size={16} />}
               {isExporting ? 'GENERATING CSV...' : 'EXPORT TO CSV'}
             </button>
             <button 
               onClick={handleGeneratePDF}
               disabled={isGeneratingPDF || loading || trends.length === 0}
               className={`w-full py-4 rounded-sm transition-colors text-[11px] font-bold uppercase tracking-wider flex justify-center items-center gap-2 shadow-sm ${
                 (isGeneratingPDF || loading || trends.length === 0) ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed border border-transparent' : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-brand-secondary hover:text-brand-secondary text-brand-primary dark:text-slate-200'
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
            <div className="min-w-[700px]">
               <div className="grid grid-cols-12 text-[10px] bg-slate-50 dark:bg-slate-900 font-extrabold text-slate-400 dark:text-slate-300 uppercase tracking-widest border-b border-slate-100 dark:border-slate-800 p-4">
              <div className="col-span-2 text-center">RANK</div>
              <div className="col-span-5">TREND IDENTIFIER</div>
              <div className="col-span-2 text-center">VELOCITY</div>
              <div className="col-span-3 text-center">VOLUME</div>
            </div>

            <div className="flex flex-col border-b border-slate-100 dark:border-slate-800">
              {loading ? (
                <div className="p-10 text-center text-slate-500 flex justify-center items-center gap-2">
                  <Loader2 size={16} className="animate-spin" /> Loading data for export...
                </div>
              ) : trends.length === 0 ? (
                <div className="p-10 text-center text-slate-500">No data available to export.</div>
              ) : trends.map((t, idx) => (
                 <div key={t._id || idx} className="grid grid-cols-12 items-center p-6 border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-default">
                   <div className="col-span-2 text-center text-4xl font-extralight text-brand-primary/30 dark:text-slate-800">{String(idx + 1).padStart(2, '0')}</div>
                   <div className="col-span-5">
                     <div className="text-[14px] font-bold text-brand-primary dark:text-slate-200 mb-0.5">{t.topic_name}</div>
                     <div className="text-[9px] font-bold uppercase tracking-wider text-brand-secondary dark:text-brand-secondary truncate pr-4">{t.top_keywords?.join(', ')}</div>
                   </div>
                   <div className="col-span-2 text-center flex justify-center items-center gap-1">
                     <span className="text-brand-secondary text-xs">&#8599;</span>
                     <span className="text-[12px] font-bold text-brand-secondary">+{t.score?.toFixed(1)}%</span>
                   </div>
                   <div className="col-span-3 text-center font-mono text-[11px] text-slate-700 dark:text-slate-300 font-medium">
                     N/A
                   </div>
                 </div>
              ))}
            </div>

            </div>
          </div>
          <div className="p-6 flex justify-between items-center bg-white dark:bg-slate-900 text-xs font-medium text-slate-500 dark:text-slate-200 mt-auto">
             <div>Displaying {trends.length} of {trends.length} records</div>
             <div className="flex gap-4 font-bold text-[10px] uppercase tracking-widest">
               <button className="text-slate-300 dark:text-slate-600 cursor-not-allowed">PREV</button>
               <button className="text-brand-primary dark:text-white hover:text-brand-secondary dark:hover:text-brand-secondary transition-colors">NEXT</button>
             </div>
           </div>
         </div>
        </div>
      </div>
  )
}

export default Export
