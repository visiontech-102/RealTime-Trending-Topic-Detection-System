import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Mail, Lock } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { GoogleLogin } from '@react-oauth/google'

const Login = () => {
  const navigate = useNavigate()
  const { login, googleLogin } = useAuth()
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')
    
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setAuthError(err.response.data.detail)
      } else {
        setAuthError('Failed to login. Please check your credentials.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setIsGoogleLoading(true)
    setAuthError('')
    
    try {
      await googleLogin(credentialResponse.credential)
      navigate('/dashboard')
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setAuthError(err.response.data.detail)
      } else {
        setAuthError(`Connection Error: ${err.message}. Is Backend running?`)
      }
      setIsGoogleLoading(false)
    }
  }

  const handleGoogleError = () => {
    setAuthError('Google Sign-In was unsuccessful or cancelled.')
  }

  return (
    <div className="flex items-center justify-center min-h-[80vh] bg-slate-50 dark:bg-slate-950 p-4 transition-colors duration-300">
      <div className="bg-white dark:bg-slate-900 p-10 shadow-lg border border-slate-100 dark:border-slate-800 rounded-sm w-full max-w-md">
        
        <div className="text-center mb-10">
          <h1 className="text-2xl font-extrabold text-brand-primary dark:text-white mb-2">Welcome Back</h1>
          <p className="text-sm text-slate-500 dark:text-slate-200">Sign in securely with your Google Account.</p>
        </div>

        <div className="flex flex-col items-center justify-center">
          {authError && (
            <div className="mb-6 w-full p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs rounded-sm font-bold text-center">
              {authError}
            </div>
          )}
          
          <form className="w-full mb-6" onSubmit={handleLogin}>
            <div className="mb-4">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  type="email"
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 dark:border-slate-700 rounded-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary focus:border-transparent dark:bg-slate-800 dark:text-white"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading || isGoogleLoading}
                  required
                />
              </div>
            </div>
            
            <div className="mb-6">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  type="password"
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 dark:border-slate-700 rounded-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary focus:border-transparent dark:bg-slate-800 dark:text-white"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading || isGoogleLoading}
                  required
                />
              </div>
            </div>
            
            <button
              type="submit"
              disabled={isLoading || isGoogleLoading}
              className="w-full flex justify-center items-center py-2 px-4 border border-transparent rounded-sm shadow-sm text-sm font-bold text-white bg-brand-primary hover:bg-brand-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary disabled:opacity-50 transition-colors"
            >
              {isLoading ? <Loader2 className="animate-spin mr-2" size={18} /> : null}
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="flex items-center w-full mb-6">
            <div className="flex-grow border-t border-slate-200 dark:border-slate-700"></div>
            <span className="px-3 text-xs text-slate-400 dark:text-slate-500 font-medium">OR</span>
            <div className="flex-grow border-t border-slate-200 dark:border-slate-700"></div>
          </div>

          <div className="w-full flex justify-center">
            {isGoogleLoading ? (
               <div className="flex flex-col items-center justify-center py-4 w-full border border-slate-200 dark:border-slate-800 rounded-sm bg-slate-50 dark:bg-slate-900/50">
                  <Loader2 className="animate-spin text-brand-secondary mb-2" size={24} />
                  <span className="text-sm text-slate-500 dark:text-slate-300 font-bold">Signing in Securely...</span>
               </div>
            ) : (
               <div className="w-full flex justify-center py-4 px-2 border border-slate-200 dark:border-slate-800 rounded-sm bg-slate-50 dark:bg-slate-900/50 shadow-inner">
                 <GoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={handleGoogleError}
                    theme="filled_blue"
                    size="large"
                    shape="rectangular"
                    width="100%"
                    text="signin_with"
                 />
               </div>
            )}
          </div>
        </div>

        <div className="text-center text-xs text-slate-500 dark:text-slate-200 border-t border-slate-100 dark:border-slate-800 pt-6 mt-8">
            Don't have an account? <Link to="/register" className="text-brand-secondary font-bold hover:underline">Register Now</Link>
        </div>
      </div>
    </div>
  )
}

export default Login
