import React, { createContext, useContext, useState } from 'react';

const DateRangeContext = createContext();

export const DateRangeProvider = ({ children }) => {
  const [range, setRange] = useState('24 HOURS');
  const [customDates, setCustomDates] = useState({
    startDate: '',
    endDate: '',
  });

  return (
    <DateRangeContext.Provider
      value={{
        range,
        setRange,
        customDates,
        setCustomDates,
      }}
    >
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => useContext(DateRangeContext);
