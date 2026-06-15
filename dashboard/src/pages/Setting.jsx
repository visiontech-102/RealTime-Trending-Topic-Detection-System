import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { 
  UserPlus, Lock, Shield, Bell, HelpCircle, Info, ChevronRight, X, CheckCircle 
} from 'lucide-react';

// Modal component
const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden m-4">
        <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h3>
          <button onClick={onClose} className="p-1 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
};

// Settings Item Component
const SettingsItem = ({ icon: Icon, title, description, onClick, className = "", isTop = false, isBottom = false }) => {
  return (
    <div 
      onClick={onClick}
      className={`group flex items-center justify-between p-4 bg-white dark:bg-[#252525] border border-slate-200 dark:border-[#333333] cursor-pointer hover:bg-slate-50 dark:hover:bg-[#2a2a2a] transition-colors
        ${isTop ? 'rounded-t-xl' : ''}
        ${isBottom ? 'rounded-b-xl border-t-0' : 'border-b-0'}
        ${!isTop && !isBottom ? 'border-y-0 border-b border-slate-200 dark:border-[#333333]' : ''}
        ${className}
      `}
    >
      <div className="flex items-center gap-4">
        {Icon && (
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-slate-100 dark:bg-[#333333] text-slate-600 dark:text-slate-300 group-hover:text-blue-500 transition-colors">
            <Icon size={20} strokeWidth={2} />
          </div>
        )}
        <div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-500 transition-colors">{title}</h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
        </div>
      </div>
      <ChevronRight size={20} className="text-slate-400 dark:text-slate-500 group-hover:text-blue-500 transition-colors" />
    </div>
  );
};

const Setting = () => {
  const { user, logout, changePassword, get2FAStatus, request2FACode, verify2FACode, disable2FA, getPreferences, updatePreferences } = useAuth();
  const navigate = useNavigate();
  
  const [activeModal, setActiveModal] = useState(null);

  // States for toggles
  const [twoFactor, setTwoFactor] = useState(false);
  const [show2FAInput, setShow2FAInput] = useState(false);
  const [twoFACode, setTwoFACode] = useState('');
  const [twoFAError, setTwoFAError] = useState('');
  const [isSending2FA, setIsSending2FA] = useState(false);
  const [isVerifying2FA, setIsVerifying2FA] = useState(false);

  React.useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [twoFAData, prefsData] = await Promise.all([
          get2FAStatus(),
          getPreferences()
        ]);
        setTwoFactor(twoFAData.two_factor_enabled);
        setEmailDigests(prefsData.email_digests);
        setSpikeAlerts(prefsData.spike_alerts);
      } catch (err) {
        console.error("Failed to fetch settings", err);
      }
    };
    fetchSettings();
  }, [get2FAStatus, getPreferences]);
  const [emailDigests, setEmailDigests] = useState(true);
  const [spikeAlerts, setSpikeAlerts] = useState(false);

  // State for password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getInitials = (name) => {
    if (!name) return "U";
    return name.substring(0, 2).toUpperCase();
  };

  const closeModal = () => {
    setActiveModal(null);
    setTimeout(() => {
      setPasswordSuccess(false);
      setPasswordError('');
      setCurrentPassword('');
      setNewPassword('');
      setShow2FAInput(false);
      setTwoFACode('');
      setTwoFAError('');
    }, 300);
  };

  const handleToggle2FA = async () => {
    if (twoFactor) {
      // Disable 2FA
      try {
        await disable2FA();
        setTwoFactor(false);
      } catch (err) {
        console.error("Failed to disable 2FA", err);
      }
    } else {
      // Enable 2FA - Request code
      setIsSending2FA(true);
      setTwoFAError('');
      try {
        await request2FACode();
        setShow2FAInput(true);
      } catch (err) {
        setTwoFAError('Failed to send code. Try again.');
      } finally {
        setIsSending2FA(false);
      }
    }
  };

  const handleVerify2FA = async (e) => {
    e.preventDefault();
    setIsVerifying2FA(true);
    setTwoFAError('');
    try {
      await verify2FACode(twoFACode);
      setTwoFactor(true);
      setShow2FAInput(false);
      setTwoFACode('');
    } catch (err) {
      if (err.response?.data?.detail) {
        setTwoFAError(err.response.data.detail);
      } else {
        setTwoFAError('Verification failed. Invalid code.');
      }
    } finally {
      setIsVerifying2FA(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setPasswordError('');
    
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setTimeout(() => {
        closeModal();
      }, 2000);
    } catch (err) {
      if (err.response && err.response.data && err.response.data.detail) {
        setPasswordError(err.response.data.detail);
      } else {
        setPasswordError('Failed to update password. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEmailDigestsToggle = async () => {
    const newVal = !emailDigests;
    setEmailDigests(newVal);
    try {
      await updatePreferences({ email_digests: newVal, spike_alerts: spikeAlerts });
    } catch (err) {
      console.error("Failed to update email digests pref", err);
      setEmailDigests(!newVal); // revert on failure
    }
  };

  const handleSpikeAlertsToggle = async () => {
    const newVal = !spikeAlerts;
    setSpikeAlerts(newVal);
    try {
      await updatePreferences({ email_digests: emailDigests, spike_alerts: newVal });
    } catch (err) {
      console.error("Failed to update spike alerts pref", err);
      setSpikeAlerts(!newVal); // revert on failure
    }
  };

  const handleAddAccount = (e) => {
    e.preventDefault();
    // To "add another account" in a standard way, we log the user out and redirect to login
    logout();
    navigate('/login');
  };

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col mb-8">
        <h1 className="text-2xl font-bold text-slate-950 dark:text-white mb-1 tracking-tight">Settings</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Configure your account and application preferences.</p>
      </div>

      <div className="flex flex-col gap-6">
        {/* ACCOUNT SECTION */}
        <div>
          <h2 className="text-xs font-bold text-slate-500 dark:text-slate-400 mb-3 uppercase tracking-wider">Account</h2>
          
          <div className="flex flex-col">
            {/* Profile Item (Top) */}
            <div 
              onClick={() => setActiveModal('profile')}
              className="group flex items-center justify-between p-4 bg-white dark:bg-[#252525] border border-slate-200 dark:border-[#333333] cursor-pointer hover:bg-slate-50 dark:hover:bg-[#2a2a2a] transition-colors rounded-t-xl"
            >
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-bold text-lg">
                  {getInitials(user?.name || 'Axmed')}
                </div>
                <div>
                  <h4 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-blue-500 transition-colors">{user?.name || 'Axmed Xasan'}</h4>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{user?.email || 'axmed@visiontech.so'}</p>
                </div>
              </div>
            </div>
            
            {/* Add another account (Middle) */}
            <SettingsItem 
              icon={UserPlus} 
              title="Add another account" 
              description="Sign in with a different account" 
              onClick={() => setActiveModal('addAccount')}
              className="border-t-0 border-b border-slate-200 dark:border-[#333333]"
            />
            
            {/* Change password (Bottom) */}
            <SettingsItem 
              icon={Lock} 
              title="Change password" 
              description="Update your login password" 
              onClick={() => setActiveModal('password')}
              isBottom={true}
            />
          </div>
        </div>

        {/* OTHER SECTIONS (Single Items) */}
        <SettingsItem 
          icon={Shield} 
          title="Privacy and security" 
          description="Two-Factor Authentication" 
          onClick={() => setActiveModal('privacy')}
          isTop={true}
          isBottom={true}
        />

        <SettingsItem 
          icon={Bell} 
          title="Notifications" 
          description="Alerts, digests, and spike notifications" 
          onClick={() => setActiveModal('notifications')}
          isTop={true}
          isBottom={true}
        />

        <div className="flex flex-col">
          <SettingsItem 
            icon={HelpCircle} 
            title="Help" 
            description="Documentation, FAQs, and support" 
            onClick={() => setActiveModal('help')}
            isTop={true}
          />
          <SettingsItem 
            icon={Info} 
            title="About" 
            description="Vision Tech v1.0 - Real-Time Topic Detection" 
            onClick={() => setActiveModal('about')}
            isBottom={true}
            className="border-t-0 border-slate-200 dark:border-[#333333]"
          />
        </div>

      </div>

      {/* MODALS */}
      <Modal isOpen={activeModal === 'profile'} onClose={closeModal} title="User Profile">
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center p-6 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
             <div className="flex items-center justify-center w-20 h-20 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 font-bold text-3xl mb-4 shadow-sm">
               {getInitials(user?.name || 'Axmed')}
             </div>
             <h3 className="text-xl font-bold text-slate-900 dark:text-white">{user?.name || 'Axmed Xasan'}</h3>
             <p className="text-sm text-slate-500 dark:text-slate-400">{user?.email || 'axmed@visiontech.so'}</p>
          </div>
          <button onClick={closeModal} className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition-colors">
            Done
          </button>
        </div>
      </Modal>

      <Modal isOpen={activeModal === 'addAccount'} onClose={closeModal} title="Add Another Account">
        <form onSubmit={handleAddAccount} className="space-y-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-sm rounded-lg mb-4">
            You will be signed out of your current account to sign in with a new one.
          </div>
          <button type="submit" className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition-colors">
            Continue to Login
          </button>
        </form>
      </Modal>

      <Modal isOpen={activeModal === 'password'} onClose={closeModal} title="Change Password">
        {passwordSuccess ? (
          <div className="flex flex-col items-center justify-center p-8 space-y-4 text-center animate-in zoom-in-95 duration-300">
            <CheckCircle size={48} className="text-green-500" />
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Password Updated</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">Your password has been changed successfully.</p>
          </div>
        ) : (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {passwordError && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs rounded-lg font-bold text-center">
                {passwordError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Current Password</label>
              <input type="password" required minLength={6} value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="••••••••" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">New Password</label>
              <input type="password" required minLength={6} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="••••••••" />
            </div>
            <button type="submit" disabled={isSubmitting} className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-70 text-white font-bold rounded-lg transition-colors">
              {isSubmitting ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        )}
      </Modal>

      <Modal isOpen={activeModal === 'privacy'} onClose={closeModal} title="Privacy & Security">
        <div className="space-y-4">
          <div 
            onClick={!show2FAInput && !isSending2FA ? handleToggle2FA : undefined}
            className={`p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center transition-colors ${!show2FAInput && !isSending2FA ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50' : 'opacity-80'}`}
          >
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">Two-Factor Authentication</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {isSending2FA ? 'Sending code...' : 'Add an extra layer of security'}
              </p>
            </div>
            <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${twoFactor ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}>
              <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all duration-300 ${twoFactor ? 'left-5' : 'left-0.5'}`}></div>
            </div>
          </div>

          {show2FAInput && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg animate-in slide-in-from-top-2 duration-300">
              <h4 className="text-sm font-bold text-blue-900 dark:text-blue-300 mb-2">Verify Email Code</h4>
              <p className="text-xs text-blue-700 dark:text-blue-400 mb-3">We've sent a 6-digit code to your email. Enter it below to enable 2FA.</p>
              
              {twoFAError && (
                <div className="mb-3 p-2 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs rounded border border-red-200 dark:border-red-800 font-bold">
                  {twoFAError}
                </div>
              )}
              
              <form onSubmit={handleVerify2FA} className="flex gap-2">
                <input 
                  type="text" 
                  value={twoFACode}
                  onChange={(e) => setTwoFACode(e.target.value)}
                  placeholder="000000" 
                  maxLength={6}
                  className="flex-1 px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <button 
                  type="submit" 
                  disabled={isVerifying2FA || twoFACode.length < 6}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-70 text-white font-bold text-sm rounded-lg transition-colors"
                >
                  {isVerifying2FA ? '...' : 'Verify'}
                </button>
              </form>
            </div>
          )}
          <button onClick={closeModal} className="w-full py-2.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-white font-bold rounded-lg transition-colors mt-4">
            Done
          </button>
        </div>
      </Modal>

      <Modal isOpen={activeModal === 'notifications'} onClose={closeModal} title="Notifications">
        <div className="space-y-4">
          <div 
            onClick={handleEmailDigestsToggle}
            className="p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
          >
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">Email Digests</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">Daily summary of trending topics</p>
            </div>
            <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${emailDigests ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}>
              <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all duration-300 ${emailDigests ? 'left-5' : 'left-0.5'}`}></div>
            </div>
          </div>

          <div 
            onClick={handleSpikeAlertsToggle}
            className="p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
          >
            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">Spike Alerts</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">Notify me on sudden topic spikes</p>
            </div>
            <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${spikeAlerts ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}>
              <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all duration-300 ${spikeAlerts ? 'left-5' : 'left-0.5'}`}></div>
            </div>
          </div>
          <button onClick={closeModal} className="w-full py-2.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-white font-bold rounded-lg transition-colors mt-4">
            Done
          </button>
        </div>
      </Modal>

      <Modal isOpen={activeModal === 'help'} onClose={closeModal} title="Help & Support">
        <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">Need assistance? Check out our resources below or contact our support team.</p>
          <div className="grid gap-2">
            <a href="#" onClick={(e) => { e.preventDefault(); window.open('https://github.com/visiontech', '_blank'); }} className="p-3 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors flex justify-between items-center">
              Read Documentation
              <ChevronRight size={16} />
            </a>
            <a href="#" onClick={(e) => e.preventDefault()} className="p-3 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors flex justify-between items-center">
              View FAQs
              <ChevronRight size={16} />
            </a>
            <a href="mailto:support@visiontech.so" className="p-3 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors flex justify-between items-center">
              Contact Support
              <ChevronRight size={16} />
            </a>
          </div>
        </div>
      </Modal>

      <Modal isOpen={activeModal === 'about'} onClose={closeModal} title="About Vision Tech">
        <div className="space-y-4 flex flex-col items-center text-center p-4">
          <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30 mb-2">
            <Shield size={32} className="text-white" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 dark:text-white">Vision Tech Topic Detection</h3>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">v1.0.0 - Final Year Project 2026</p>
          
          <div className="w-full h-px bg-slate-200 dark:bg-slate-800 my-2"></div>
          
          <div className="text-sm text-slate-600 dark:text-slate-300 space-y-3 text-left w-full bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
            <div>
              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Developers</p>
              <p className="font-medium text-slate-900 dark:text-white">Vision Tech Team</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">System</p>
              <p className="font-medium text-slate-900 dark:text-white">Real-Time Trending Topic Detection System for Somali Language</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">Institution</p>
              <p className="font-medium text-slate-900 dark:text-white">Jamhuriya University of Science and Technology (JUST)</p>
            </div>
          </div>
          
          <div className="w-full h-px bg-slate-200 dark:bg-slate-800 my-2"></div>
          <p className="text-xs text-slate-500 dark:text-slate-400">© 2026 Vision Tech Group 102. All rights reserved.</p>
        </div>
      </Modal>

    </div>
  );
};

export default Setting;
