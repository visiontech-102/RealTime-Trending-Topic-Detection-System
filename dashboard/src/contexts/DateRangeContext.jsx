import React, { createContext, useContext, useState, useMemo } from 'react';

const DateRangeContext = createContext();

export const DateRangeProvider = ({ children }) => {
  const [range, setRangeState] = useState(() => {
    return localStorage.getItem('visiontech_time_range') || '24h';
  });

  const [customDates, setCustomDatesState] = useState(() => {
    const saved = localStorage.getItem('visiontech_custom_dates');
    return saved ? JSON.parse(saved) : { startDate: '', endDate: '' };
  });

  const setRange = (newRange) => {
    setRangeState(newRange);
    localStorage.setItem('visiontech_time_range', newRange);
  };

  const setCustomDates = (newDates) => {
    setCustomDatesState(newDates);
    localStorage.setItem('visiontech_custom_dates', JSON.stringify(newDates));
  };

  // Compute startDate and endDate dynamically from the selected range and custom dates
  const calculatedDates = useMemo(() => {
    const now = new Date();
    let start = new Date(now);
    let end = new Date(now);

    if (range === '24h') {
      start.setHours(start.getHours() - 24);
    } else if (range === '7d') {
      start.setDate(start.getDate() - 7);
    } else if (range === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (range === 'custom' && customDates.startDate && customDates.endDate) {
      start = new Date(`${customDates.startDate}T00:00:00`);
      end = new Date(`${customDates.endDate}T23:59:59`);
    } else {
      // Default fallback
      start.setHours(start.getHours() - 24);
    }

    return {
      startDate: start.toISOString(),
      endDate: end.toISOString()
    };
  }, [range, customDates]);

  return (
    <DateRangeContext.Provider
      value={{
        range,
        setRange,
        customDates,
        setCustomDates,
        startDate: calculatedDates.startDate,
        endDate: calculatedDates.endDate
      }}
    >
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => useContext(DateRangeContext);

