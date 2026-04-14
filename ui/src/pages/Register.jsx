import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const Register = () => {
  const navigate = useNavigate()
  const { signup } = useAuth()
  
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [confirmError, setConfirmError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleEmailChange = (e) => {
    const value = e.target.value
    setEmail(value)
    
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
    
    if (confirmPassword && value !== confirmPassword) {
      setConfirmError('Passwords do not match')
    } else if (confirmPassword && value === confirmPassword) {
      setConfirmError('')
    }
  }

  const handleConfirmChange = (e) => {
    const value = e.target.value
    setConfirmPassword(value)
    
    if (value && value !== password) {
      setConfirmError('Passwords do not match')
    } else {
      setConfirmError('')
    }
  }

  const handleRegister = (e) => {
    e.preventDefault()
    
    if (emailError || passwordError || confirmError || !email || !password || !fullName || password !== confirmPassword) {
      return;
    }

    setIsLoading(true)
    
    signup(fullName, email, password)
    
    setTimeout(() => {
      setIsLoading(false)
      navigate('/dashboard')
    }, 1200)
  }

  const isValid = !emailError && !passwordError && !confirmError && 
                  email.length > 0 && password.length >= 8 && fullName.length > 0 && 
                  password === confirmPassword

  return (
    <div className="flex items-center justify-center min-h-[80vh] bg-slate-50 dark:bg-slate-950 p-4 transition-colors duration-300">
      <div className="bg-white dark:bg-slate-900 p-10 shadow-lg border border-slate-100 dark:border-slate-800 rounded-sm w-full max-w-md">
        
        <div className="text-center mb-8">
          <h1 className="text-2xl font-extrabold text-brand-primary dark:text-white mb-2">Create Account</h1>
          <p className="text-sm text-slate-500 dark:text-slate-200">Join the real-time trend detection network.</p>
        </div>

        <form onSubmit={handleRegister}>
          <div className="mb-4">
            <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
              Full Name
            </label>
            <input 
              type="text" 
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Enter your full name"
              className="w-full text-sm p-3 outline-none border rounded-sm transition-colors bg-transparent placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white border-slate-200 dark:border-slate-700 focus:border-brand-secondary"
              required 
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input 
              type="email" 
              value={email}
              onChange={handleEmailChange}
              placeholder="name@organization.com"
              className={`w-full text-sm p-3 outline-none border rounded-sm transition-colors bg-transparent placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white 
                ${emailError 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-slate-200 dark:border-slate-700 focus:border-brand-secondary'}`}
              required 
            />
            {emailError && <p className="text-red-500 text-xs mt-1">{emailError}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-8">
             <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
                  Password
                </label>
                <input 
                  type="password" 
                  value={password}
                  onChange={handlePasswordChange}
                  placeholder="••••••••"
                  className={`w-full text-sm p-3 outline-none border rounded-sm transition-colors bg-transparent placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white tracking-widest
                    ${passwordError 
                      ? 'border-red-500 focus:border-red-500' 
                      : 'border-slate-200 dark:border-slate-700 focus:border-brand-secondary'}`}
                  required 
                />
                {passwordError && <p className="text-red-500 text-xs mt-1">{passwordError}</p>}
             </div>
             <div>
                <label className="block text-[11px] font-bold text-slate-500 dark:text-slate-200 uppercase tracking-wider mb-2">
                  Confirm
                </label>
                <input 
                  type="password" 
                  value={confirmPassword}
                  onChange={handleConfirmChange}
                  placeholder="••••••••"
                  className={`w-full text-sm p-3 outline-none border rounded-sm transition-colors bg-transparent placeholder:text-slate-300 dark:placeholder:text-slate-400 text-slate-900 dark:text-white tracking-widest
                    ${confirmError 
                      ? 'border-red-500 focus:border-red-500' 
                      : 'border-slate-200 dark:border-slate-700 focus:border-brand-secondary'}`}
                  required 
                />
                {confirmError && <p className="text-red-500 text-xs mt-1">{confirmError}</p>}
             </div>
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
                <span>Processing...</span>
              </>
            ) : (
              <>
                Register Account <span>&rarr;</span>
              </>
            )}
          </button>

          <div className="text-center text-xs text-slate-500 dark:text-slate-200 border-t border-slate-100 dark:border-slate-800 pt-6 mt-6">
             Already have an account? <Link to="/login" className="text-brand-secondary font-bold hover:underline">Log In</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Register
