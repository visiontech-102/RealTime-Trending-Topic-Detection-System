import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import { DateRangeProvider } from './contexts/DateRangeContext'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <LanguageProvider>
          <DateRangeProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </DateRangeProvider>
        </LanguageProvider>
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
