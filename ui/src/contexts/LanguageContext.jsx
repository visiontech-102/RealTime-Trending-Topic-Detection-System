import React, { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    dashboard: "Dashboard",
    history: "History",
    comparison: "Comparison",
    export: "Export",
    settings: "Settings",
    profile: "Profile",
    login: "Login",
    signup: "Sign Up",
    logout: "Logout",
    welcome: "Welcome back",
    trends: "Real-Time Trends",
    volume: "Volume",
    keywords: "Keywords",
    engagement: "Engagement",
    english: "English",
    somali: "Somali",
    themeMode: "Theme Mode",
    language: "Language",
    save: "Save Changes",
    email: "Email Address",
    password: "Password",
    download: "Download",
    search: "Search...",
    dateRange: "Date Range",
    exportData: "Export Data",
    compareLang: "Compare Languages",
    username: "Username",
    systemPref: "System Preferences",
    apiStatus: "API Status",
    connected: "Connected",
    disconnected: "Disconnected",
    noData: "No data available",
    loading: "Loading..."
  },
  so: {
    dashboard: "Shaashadda Weyn",
    history: "Taariikhda",
    comparison: "Isbarbardhig",
    export: "Dhoofi Xogta",
    settings: "Nidaaminta",
    profile: "Akoonka",
    login: "Gal",
    signup: "Isdiiwaangeli",
    logout: "Ka Bax",
    welcome: "Kusoo Dhawoow",
    trends: "Isbeddellada Waqtiga-Dhabta ah",
    volume: "Mugga",
    keywords: "Ereyada Muhiimka ah",
    engagement: "Hawsheeda",
    english: "Ingiriisi",
    somali: "Soomaali",
    themeMode: "Nashqada Midabka",
    language: "Luqadda",
    save: "Keydi Isbedelada",
    email: "Iimaylka",
    password: "Furaha",
    download: "Soo deji",
    search: "Raadi...",
    dateRange: "Xilliga",
    exportData: "Dhoofi Xogta",
    compareLang: "Isbarbardhig Luqadaha",
    username: "Magaca Isticmaalaha",
    systemPref: "Xulashada Nidaamka",
    apiStatus: "Xaaladda API",
    connected: "Wuu Ku Xiran Yahay",
    disconnected: "Wuu Ka Goyan Yahay",
    noData: "Xog Lama Helin",
    loading: "Wuu Soo Shubanayaa..."
  }
};

const LanguageContext = createContext();

export const useLanguage = () => useContext(LanguageContext);

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('language') || 'en';
  });

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'so' : 'en');
  };

  const t = (key) => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};
