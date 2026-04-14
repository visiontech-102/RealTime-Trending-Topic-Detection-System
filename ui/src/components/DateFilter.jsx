import React, { useState, useRef, useEffect } from 'react';
import { Calendar as CalendarIcon, ArrowUp, ArrowDown } from 'lucide-react';
import { useDateRange } from '../contexts/DateRangeContext';

// Formatter to match native mm/dd/yyyy if needed
const formatDateForInput = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const pad = (n) => n.toString().padStart(2, '0');
  return `${pad(d.getMonth() + 1)}/${pad(d.getDate())}/${d.getFullYear()}`;
};

const CustomNativePicker = ({ value, onChange, min, onClose }) => {
  const [viewDate, setViewDate] = useState(value ? new Date(value) : new Date());

  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

  const handlePrevMonth = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  const handleNextMonth = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));

  const handleDateClick = (day) => {
    const d = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
    if (min && d < new Date(min)) return;
    const pad = (n) => n.toString().padStart(2, '0');
    onChange(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`);
    onClose();
  };

  const setToday = () => {
    const d = new Date();
    const pad = (n) => n.toString().padStart(2, '0');
    onChange(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`);
    onClose();
  };

  const renderDays = () => {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const daysInMonth = getDaysInMonth(year, month);
    const firstDay = getFirstDayOfMonth(year, month);
    const daysInPrevMonth = getDaysInMonth(year, month - 1);

    const days = [];
    
    // Prev Month
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`prev-${i}`} className="text-slate-300 dark:text-slate-600 text-sm py-1 text-center">{daysInPrevMonth - firstDay + i + 1}</div>);
    }

    // Current Month
    for (let day = 1; day <= daysInMonth; day++) {
      const currentDateStr = `${year}-${(month+1).toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      const isSelected = value === currentDateStr;
      const isPastMin = min && new Date(currentDateStr) < new Date(min);
      
      let className = "text-sm py-1 cursor-pointer transition-colors text-center ";
      
      if (isSelected) {
        // MATCHING DEEP BLUE / VIBRANT CYAN HERE
        className += "bg-brand-primary dark:bg-brand-secondary text-white font-bold border-2 border-brand-secondary rounded-sm";
      } else if (isPastMin) {
        className += "text-slate-300 cursor-not-allowed";
      } else {
        className += "text-brand-primary dark:text-slate-200 hover:bg-brand-secondary/20 hover:text-brand-primary rounded-sm";
      }

      days.push(
        <div key={`day-${day}`} className={className} onClick={() => !isPastMin && handleDateClick(day)}>
          {day}
        </div>
      );
    }

    // Next Month padding
    const remaining = 42 - days.length; // 6 rows of 7
    for (let i = 1; i <= remaining; i++) {
       days.push(<div key={`next-${i}`} className="text-slate-300 dark:text-slate-600 text-sm py-1 text-center">{i}</div>);
    }

    return days;
  };

  return (
    <div className="absolute top-12 left-0 w-64 bg-white dark:bg-slate-900 border border-brand-secondary/30 rounded-md shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95">
      {/* Header Month / Arrows */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-brand-primary dark:text-white font-bold cursor-pointer hover:text-brand-secondary flex items-center gap-1">
          {viewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          <ArrowDown size={12} className="opacity-50" />
        </h3>
        <div className="flex gap-2">
          <button onClick={handlePrevMonth} className="text-brand-primary dark:text-slate-400 hover:text-brand-secondary p-1"><ArrowUp size={16}/></button>
          <button onClick={handleNextMonth} className="text-brand-primary dark:text-slate-400 hover:text-brand-secondary p-1"><ArrowDown size={16}/></button>
        </div>
      </div>

      {/* Weekdays */}
      <div className="grid grid-cols-7 mb-2">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
          <div key={d} className="text-brand-primary dark:text-slate-400 text-sm text-center">{d}</div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-y-1 mb-4">
        {renderDays()}
      </div>

      {/* Footer native buttons */}
      <div className="flex justify-between items-center pt-3 border-t border-slate-100 dark:border-slate-800">
        <button onClick={() => { onChange(''); onClose(); }} className="text-brand-secondary dark:text-brand-secondary text-sm hover:underline">Clear</button>
        <button onClick={setToday} className="text-brand-secondary dark:text-brand-secondary text-sm hover:underline">Today</button>
      </div>
    </div>
  );
};

const DateFilter = () => {
  const { range, setRange, customDates, setCustomDates } = useDateRange();
  const [showDatePicker, setShowDatePicker] = useState(false);
  
  const [tempStart, setTempStart] = useState(customDates.startDate || '');
  const [tempEnd, setTempEnd] = useState(customDates.endDate || '');

  const [activePicker, setActivePicker] = useState(null); // 'start' or 'end'

  const popupRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (popupRef.current && !popupRef.current.contains(event.target)) {
         setShowDatePicker(false);
         setActivePicker(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleApplyCustom = () => {
    if (tempStart && tempEnd) {
      setCustomDates({ startDate: tempStart, endDate: tempEnd });
      setRange('CUSTOM RANGE');
      setShowDatePicker(false);
    }
  };

  const isCustomActive = range === 'CUSTOM RANGE';

  return (
    <div className="relative inline-flex items-center gap-2">
      {['24 HOURS', '7 DAYS', '30 DAYS'].map((r) => (
        <button
          key={r}
          onClick={() => setRange(r)}
          className={`px-4 py-2 rounded-sm text-[10px] font-extrabold uppercase tracking-widest transition-colors ${
            range === r
              ? 'bg-brand-secondary text-slate-950'
              : 'bg-slate-100/50 dark:bg-slate-800/50 text-brand-primary dark:text-slate-300 hover:bg-brand-secondary hover:text-slate-950 dark:hover:bg-brand-secondary dark:hover:text-slate-950'
          }`}
        >
          {r}
        </button>
      ))}

      <div ref={popupRef} className="relative ml-2">
        <button
          onClick={() => setShowDatePicker(!showDatePicker)}
          className={`px-4 py-2 border rounded-sm text-[10px] font-extrabold uppercase tracking-widest transition-colors flex items-center gap-2 ${
            isCustomActive || showDatePicker
              ? 'bg-brand-secondary text-slate-950 border-brand-secondary'
              : 'border-brand-primary dark:border-slate-700 text-brand-primary dark:text-slate-200 hover:bg-brand-secondary hover:text-slate-950 hover:border-brand-secondary'
          }`}
        >
          <CalendarIcon size={12} /> CUSTOM RANGE
        </button>

        {showDatePicker && (
          <div className="absolute right-0 top-full mt-2 w-[400px] bg-white dark:bg-slate-900 border border-brand-secondary/30 rounded-xl shadow-2xl z-50 p-5 animate-in fade-in zoom-in duration-200">
             
             {/* Header Inputs */}
             <div className="flex gap-4 mb-6">
                <div className="flex-1 relative">
                  <label className="block text-[10px] font-extrabold text-brand-primary dark:text-brand-secondary uppercase tracking-widest mb-1.5">START DATE</label>
                  <div 
                    onClick={() => setActivePicker(activePicker === 'start' ? null : 'start')}
                    className={`flex items-center justify-between border ${activePicker === 'start' ? 'border-brand-secondary ring-2 ring-brand-secondary/20' : 'border-slate-200 dark:border-slate-700'} bg-slate-50 dark:bg-slate-800 rounded-lg p-2.5 cursor-pointer hover:border-brand-secondary transition-colors`}
                  >
                    <span className={`text-sm font-medium ${tempStart ? 'text-brand-primary dark:text-white' : 'text-slate-400'}`}>
                      {tempStart ? formatDateForInput(tempStart) : 'mm/dd/yyyy'}
                    </span>
                    <CalendarIcon size={16} className={`${activePicker === 'start' ? 'text-brand-secondary' : 'text-slate-400'}`} />
                  </div>
                  {activePicker === 'start' && (
                    <CustomNativePicker 
                      value={tempStart} 
                      onChange={setTempStart} 
                      onClose={() => setActivePicker(null)} 
                    />
                  )}
                </div>
                <div className="flex-1 relative">
                  <label className="block text-[10px] font-extrabold text-brand-primary dark:text-brand-secondary uppercase tracking-widest mb-1.5">END DATE</label>
                  <div 
                    onClick={() => setActivePicker(activePicker === 'end' ? null : 'end')}
                    className={`flex items-center justify-between border ${activePicker === 'end' ? 'border-brand-secondary ring-2 ring-brand-secondary/20' : 'border-slate-200 dark:border-slate-700'} bg-slate-50 dark:bg-slate-800 rounded-lg p-2.5 cursor-pointer hover:border-brand-secondary transition-colors`}
                  >
                    <span className={`text-sm font-medium ${tempEnd ? 'text-brand-primary dark:text-white' : 'text-slate-400'}`}>
                      {tempEnd ? formatDateForInput(tempEnd) : 'mm/dd/yyyy'}
                    </span>
                    <CalendarIcon size={16} className={`${activePicker === 'end' ? 'text-brand-secondary' : 'text-slate-400'}`} />
                  </div>
                  {activePicker === 'end' && (
                    <CustomNativePicker 
                      value={tempEnd} 
                      min={tempStart} 
                      onChange={setTempEnd} 
                      onClose={() => setActivePicker(null)} 
                    />
                  )}
                </div>
             </div>

             <div className="mb-6 text-center text-xs text-brand-primary/70 dark:text-slate-400 px-2 leading-relaxed">
               Click on the date fields above to select your custom timeframe using the tailored calendar.
             </div>

             <div className="flex justify-between items-center pt-4 border-t border-slate-100 dark:border-slate-800">
                <button 
                  onClick={() => setShowDatePicker(false)} 
                  className="text-brand-primary dark:text-brand-secondary text-sm font-bold hover:opacity-70 py-2 px-4 transition-opacity"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleApplyCustom}
                  disabled={!tempStart || !tempEnd}
                  className="bg-brand-secondary hover:bg-brand-primary disabled:opacity-50 disabled:cursor-not-allowed hover:text-white text-slate-950 text-xs font-extrabold uppercase tracking-widest py-3 px-6 rounded-md transition-colors shadow-sm"
                >
                  APPLY RANGE
                </button>
             </div>

          </div>
        )}
      </div>
    </div>
  );
};

export default DateFilter;
