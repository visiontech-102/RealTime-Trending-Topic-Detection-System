import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Mail, Lock, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { GoogleLogin } from '@react-oauth/google'

const Register = () => {
  const navigate = useNavigate()
  const { signup, googleLogin } = useAuth()
  
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  
  const [authError, setAuthError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  const handleSignup = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')
    setSuccessMsg('')
    
    try {
      await signup(username, email, password)
      navigate('/login')
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setAuthError(err.response.data.detail)
      } else {
        setAuthError('Failed to create account. Please check your details.')
      }
      setIsLoading(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setIsGoogleLoading(true)
    setAuthError('')
    setSuccessMsg('')
    
    try {
      await googleLogin(credentialResponse.credential)
      setSuccessMsg("Welcome! Your account has been created successfully. Redirecting to dashboard...")
      setTimeout(() => {
        navigate('/dashboard')
      }, 2000)
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setAuthError(err.response.data.detail)
      } else {
        setAuthError('Failed to verify Google account. Please try again.')
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
          <h1 className="text-2xl font-extrabold text-brand-primary dark:text-white mb-2">Create Account</h1>
          <p className="text-sm text-slate-500 dark:text-slate-200">Join the real-time trend detection network.<br/>Sign up with your email or securely via Google.</p>
        </div>

        <div className="flex flex-col items-center justify-center">
          {successMsg && (
            <div className="mb-6 w-full p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-sm font-bold text-center rounded-sm">
              {successMsg}
            </div>
          )}
          {authError && (
            <div className="mb-6 w-full p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs rounded-sm font-bold text-center">
              {authError}
            </div>
          )}
          
          
          <form className="w-full mb-6" onSubmit={handleSignup}>
            <div className="mb-4">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Username</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  type="text"
                  className="w-full pl-10 pr-3 py-2 border border-slate-300 dark:border-slate-700 rounded-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary focus:border-transparent dark:bg-slate-800 dark:text-white"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading || isGoogleLoading}
                  required
                />
              </div>
            </div>

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
                  placeholder="Create a password"
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
              {isLoading ? 'Processing...' : 'Register'}
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
                  <span className="text-sm text-slate-500 dark:text-slate-300 font-bold">Verifying Secure Token...</span>
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
                    text="signup_with"
                 />
               </div>
            )}
          </div>
        </div>

        <div className="text-center text-xs text-slate-500 dark:text-slate-200 border-t border-slate-100 dark:border-slate-800 pt-6 mt-8">
            Already have an account? <Link to="/login" className="text-brand-secondary font-bold hover:underline">Log In</Link>
        </div>
      </div>
    </div>
  )
}

export default Register
