import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const Login = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleEmailChange = (e) => {
    const value = e.target.value
    setEmail(value)
    
    // RegEx validation for standard email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (value && !emailRegex.test(value)) {
      setEmailError('Invalid email format')
    } else {
      setEmailError('')
    }
  }

  const handlePasswordChange = (e) => {
    const value = e.target.value
    setPassword(value)
    
    if (value && value.length < 8) {
      setPasswordError('Password must be at least 8 characters')
    } else {
      setPasswordError('')
    }
  }

  const handleLogin = (e) => {
    e.preventDefault()
    
    // Basic catch
    if (emailError || passwordError || !email || !password) {
      return;
    }

    setIsLoading(true)
    
    // Simulate API call and redirect
    login(email, password)
    setTimeout(() => {
      setIsLoading(false)
      navigate('/dashboard')
    }, 1200)
  }

  const isValid = !emailError && !passwordError && email.length > 0 && password.length >= 8

  return (
    <div className="flex items-center justify-center min-h-[80vh] bg-slate-50 dark:bg-slate-950 p-4 transition-colors duration-300">
      <div className="bg-white dark:bg-slate-900 p-10 shadow-lg border border-slate-100 dark:border-slate-800 rounded-sm w-full max-w-sm">
        
        <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-brand-primary dark:text-white mb-2">Welcome Back</h1>
            <p className="text-sm text-slate-500 dark:text-slate-200">Sign in to the Vision Tech system</p>
        </div>

        <form onSubmit={handleLogin}>
          <div className="mb-6">
            <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input 
              type="email" 
              value={email}
              onChange={handleEmailChange}
              placeholder="curator@visiontech.io"
              className={`w-full text-sm outline-none border-b pb-2 bg-transparent transition-colors placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white
                ${emailError 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-slate-200 dark:border-slate-700 focus:border-brand-secondary'}`}
              required 
            />
            {emailError && <p className="text-red-500 text-xs mt-1">{emailError}</p>}
          </div>
          
          <div className="mb-8">
            <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
              Password
            </label>
            <input 
              type="password" 
              value={password}
              onChange={handlePasswordChange}
              placeholder="••••••••"
              className={`w-full text-sm outline-none border-b pb-2 bg-transparent transition-colors placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white tracking-widest
                ${passwordError 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-slate-200 dark:border-slate-700 focus:border-brand-secondary'}`}
              required 
            />
            {passwordError && <p className="text-red-500 text-xs mt-1">{passwordError}</p>}
          </div>

          <button 
            type="submit" 
            disabled={!isValid || isLoading}
            className={`w-full py-3 text-sm font-semibold rounded-sm mb-6 flex justify-center items-center gap-2 transition-all duration-200
              ${(!isValid || isLoading)
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-300 cursor-not-allowed' 
                : 'bg-brand-primary text-white hover:bg-brand-primary/90'
              }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin text-brand-secondary" size={20} />
                <span>Authorizing...</span>
              </>
            ) : (
              'SIGN IN'
            )}
          </button>

          <div className="text-center text-xs text-slate-500 dark:text-slate-200">
            New to the curator? <Link to="/register" className="text-brand-secondary font-semibold hover:underline">Create an account</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Login
