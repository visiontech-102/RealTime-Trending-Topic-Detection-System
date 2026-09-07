import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Mail, Lock, ShieldCheck, ArrowLeft } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { GoogleLogin } from '@react-oauth/google'

const Login = () => {
  const navigate = useNavigate()
  const { login, completeLogin2FA, googleLogin } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(
    // Set by the API layer when a request was rejected with an expired token.
    new URLSearchParams(window.location.search).has('expired')
      ? 'Your session expired. Please sign in again.'
      : ''
  )
  const [isLoading, setIsLoading] = useState(false)
  const [isGoogleLoading, setIsGoogleLoading] = useState(false)

  // Second login step. A challenge token means the password was accepted but no
  // session exists yet — it is only exchanged for a real token by /auth/login/2fa.
  const [challengeToken, setChallengeToken] = useState(null)
  const [twoFACode, setTwoFACode] = useState('')
  const [devCode, setDevCode] = useState(null)
  const [isVerifying, setIsVerifying] = useState(false)

  const readError = (err, fallback) =>
    err?.response?.data?.detail || fallback

  const handleAuthResult = (result) => {
    if (result?.requires2FA) {
      setChallengeToken(result.challengeToken)
      setDevCode(result.devCode)
      return
    }
    navigate('/dashboard')
  }

  const resetTo2FAStart = () => {
    setChallengeToken(null)
    setTwoFACode('')
    setDevCode(null)
    setAuthError('')
    setPassword('')
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')

    try {
      handleAuthResult(await login(email, password))
    } catch (err) {
      setAuthError(readError(err, 'Failed to login. Please check your credentials.'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerify2FA = async (e) => {
    e.preventDefault()
    setIsVerifying(true)
    setAuthError('')

    try {
      await completeLogin2FA(challengeToken, twoFACode)
      navigate('/dashboard')
    } catch (err) {
      setAuthError(readError(err, 'Verification failed. Please try again.'))
      setTwoFACode('')
    } finally {
      setIsVerifying(false)
    }
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setIsGoogleLoading(true)
    setAuthError('')

    try {
      handleAuthResult(await googleLogin(credentialResponse.credential))
    } catch (err) {
      setAuthError(readError(err, `Connection Error: ${err.message}. Is Backend running?`))
    } finally {
      setIsGoogleLoading(false)
    }
  }

  const handleGoogleError = () => {
    setAuthError('Google Sign-In was unsuccessful or cancelled.')
  }

  const errorBanner = authError && (
    <div className="mb-6 w-full p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs rounded-sm font-bold text-center">
      {authError}
    </div>
  )

  if (challengeToken) {
    return (
      <div className="flex items-center justify-center min-h-[80vh] bg-slate-50 dark:bg-slate-950 p-4 transition-colors duration-300">
        <div className="bg-white dark:bg-slate-900 p-10 shadow-lg border border-slate-100 dark:border-slate-800 rounded-sm w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 flex items-center justify-center">
              <ShieldCheck className="text-brand-primary dark:text-brand-secondary" size={28} />
            </div>
            <h1 className="text-2xl font-extrabold text-brand-primary dark:text-white mb-2">Two-Factor Verification</h1>
            <p className="text-sm text-slate-500 dark:text-slate-300">
              We sent a 6-digit code to your email. It expires in 10 minutes.
            </p>
          </div>

          {errorBanner}

          {devCode && (
            <div className="mb-6 w-full p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 text-xs rounded-sm text-center">
              Dev mode — email delivery is off. Code: <span className="font-mono font-bold">{devCode}</span>
            </div>
          )}

          <form onSubmit={handleVerify2FA}>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              autoFocus
              value={twoFACode}
              onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="w-full px-3 py-3 mb-6 border border-slate-300 dark:border-slate-700 rounded-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary dark:bg-slate-800 dark:text-white text-center text-2xl font-mono tracking-[0.4em]"
              required
            />

            <button
              type="submit"
              disabled={isVerifying || twoFACode.length < 6}
              className="w-full flex justify-center items-center py-2 px-4 border border-transparent rounded-sm shadow-sm text-sm font-bold text-white bg-brand-primary hover:bg-brand-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary disabled:opacity-50 transition-colors"
            >
              {isVerifying ? <Loader2 className="animate-spin mr-2" size={18} /> : null}
              {isVerifying ? 'Verifying...' : 'Verify and Sign In'}
            </button>
          </form>

          <button
            onClick={resetTo2FAStart}
            className="w-full flex items-center justify-center gap-2 mt-6 text-xs font-bold text-slate-500 dark:text-slate-400 hover:text-brand-secondary transition-colors"
          >
            <ArrowLeft size={14} /> Back to sign in
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[80vh] bg-slate-50 dark:bg-slate-950 p-4 transition-colors duration-300">
      <div className="bg-white dark:bg-slate-900 p-10 shadow-lg border border-slate-100 dark:border-slate-800 rounded-sm w-full max-w-md">
        
        <div className="text-center mb-10">
          <h1 className="text-2xl font-extrabold text-brand-primary dark:text-white mb-2">Welcome Back</h1>
          <p className="text-sm text-slate-500 dark:text-slate-200">Sign in securely with your Google Account.</p>
        </div>

        <div className="flex flex-col items-center justify-center">
          {errorBanner}

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
                    width="320"
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
