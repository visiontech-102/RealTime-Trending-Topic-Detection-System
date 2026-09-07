import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  Lock, Shield, Bell, Info, ChevronRight, X, CheckCircle, Loader2
} from 'lucide-react';

const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden m-4">
        <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
          <h3 className="text-lg font-bold text-brand-primary dark:text-white">{title}</h3>
          <button onClick={onClose} className="p-1 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
};

const Toggle = ({ enabled }) => (
  <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${enabled ? 'bg-brand-primary' : 'bg-slate-300 dark:bg-slate-600'}`}>
    <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all duration-300 ${enabled ? 'left-5' : 'left-0.5'}`} />
  </div>
);

const SettingsItem = ({ icon: Icon, title, description, onClick, className = '', isTop = false, isBottom = false }) => (
  <div
    onClick={onClick}
    className={`group flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors
      ${isTop ? 'rounded-t-xl' : ''}
      ${isBottom ? 'rounded-b-xl' : 'border-b-0'}
      ${isBottom && !isTop ? 'border-t-0' : ''}
      ${!isTop && !isBottom ? 'border-y-0 border-b border-slate-200 dark:border-slate-800' : ''}
      ${className}
    `}
  >
    <div className="flex items-center gap-4">
      {Icon && (
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary dark:text-brand-secondary group-hover:bg-brand-primary group-hover:text-white transition-colors">
          <Icon size={20} strokeWidth={2} />
        </div>
      )}
      <div>
        <h4 className="text-sm font-bold text-brand-primary dark:text-white group-hover:text-brand-secondary dark:group-hover:text-brand-secondary transition-colors">{title}</h4>
        <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
      </div>
    </div>
    <ChevronRight size={20} className="text-slate-400 dark:text-slate-500 group-hover:text-brand-secondary transition-colors" />
  </div>
);

const Setting = () => {
  const { user, changePassword, get2FAStatus, request2FACode, verify2FACode, disable2FA, getPreferences, updatePreferences } = useAuth();

  const [activeModal, setActiveModal] = useState(null);
  const [confirm2FADisable, setConfirm2FADisable] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableError, setDisableError] = useState('');
  const [isDisabling, setIsDisabling] = useState(false);
  // Google-provisioned accounts have no password their owner knows, so an
  // emailed code is offered as an equally strong second way to re-authenticate.
  const [disableMode, setDisableMode] = useState('password');
  const [disableCode, setDisableCode] = useState('');
  const [isSendingDisableCode, setIsSendingDisableCode] = useState(false);
  const [twoFactor, setTwoFactor] = useState(false);
  const [show2FAInput, setShow2FAInput] = useState(false);
  const [twoFACode, setTwoFACode] = useState('');
  const [twoFAError, setTwoFAError] = useState('');
  const [twoFANotice, setTwoFANotice] = useState('');
  const [isSending2FA, setIsSending2FA] = useState(false);
  const [isVerifying2FA, setIsVerifying2FA] = useState(false);
  const [emailDigests, setEmailDigests] = useState(true);
  const [spikeAlerts, setSpikeAlerts] = useState(false);
  const [isSavingDigests, setIsSavingDigests] = useState(false);
  const [isSavingSpike, setIsSavingSpike] = useState(false);
  const [notifStatus, setNotifStatus] = useState(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  React.useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [twoFAData, prefsData] = await Promise.all([get2FAStatus(), getPreferences()]);
        setTwoFactor(twoFAData.two_factor_enabled);
        setEmailDigests(prefsData.email_digests);
        setSpikeAlerts(prefsData.spike_alerts);
      } catch (err) {
        console.error('Failed to fetch settings', err);
      }
    };
    fetchSettings();
  }, []);

  const getInitials = (name) => (!name ? 'U' : name.substring(0, 2).toUpperCase());

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
      setTwoFANotice('');
      setConfirm2FADisable(false);
      setDisablePassword('');
      setDisableError('');
      setDisableCode('');
      setDisableMode('password');
    }, 300);
  };

  const handleToggle2FA = async () => {
    if (twoFactor) {
      setConfirm2FADisable(true);
      return;
    }

    setIsSending2FA(true); setTwoFAError(''); setTwoFANotice('');
    try {
      await request2FACode();
      setShow2FAInput(true);
    } catch (err) {
      // 429 means a code went out moments ago and is still valid, so open the
      // input anyway — the resend throttle should not become a dead end.
      if (err.response?.status === 429) {
        setShow2FAInput(true);
        setTwoFANotice(err.response.data?.detail || 'A code was already sent. Check your email.');
      } else {
        setTwoFAError(err.response?.data?.detail || 'Failed to send code. Try again.');
      }
    } finally { setIsSending2FA(false); }
  };

  const handleSwitchToCodeDisable = async () => {
    setIsSendingDisableCode(true); setDisableError('');
    try {
      await request2FACode();
      setDisableMode('code');
    } catch (err) {
      // A live code from the resend cooldown is still usable, so switch anyway.
      if (err.response?.status === 429) {
        setDisableMode('code');
        setDisableError(err.response.data?.detail || 'A code was already sent. Check your email.');
      } else {
        setDisableError(err.response?.data?.detail || 'Failed to send code. Try again.');
      }
    } finally { setIsSendingDisableCode(false); }
  };

  const handleConfirmDisable2FA = async (e) => {
    e.preventDefault();
    setIsDisabling(true); setDisableError('');
    try {
      await disable2FA(
        disableMode === 'code' ? { code: disableCode.trim() } : { password: disablePassword }
      );
      setTwoFactor(false); setConfirm2FADisable(false);
      setDisablePassword(''); setDisableCode(''); setDisableMode('password');
    } catch (err) {
      setDisableError(err.response?.data?.detail || 'Failed to disable 2FA. Please try again.');
    } finally { setIsDisabling(false); }
  };

  const handleVerify2FA = async (e) => {
    e.preventDefault(); setIsVerifying2FA(true); setTwoFAError('');
    try {
      await verify2FACode(twoFACode.trim());
      setTwoFactor(true); setShow2FAInput(false); setTwoFACode('');
    } catch (err) {
      setTwoFAError(err.response?.data?.detail || 'Verification failed. Invalid code.');
    } finally { setIsVerifying2FA(false); }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault(); setIsSubmitting(true); setPasswordError('');
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordSuccess(true); setCurrentPassword(''); setNewPassword('');
      setTimeout(closeModal, 2000);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to update password. Please try again.');
    } finally { setIsSubmitting(false); }
  };

  const _showNotifStatus = (type, msg) => {
    setNotifStatus({ type, msg });
    if (type === 'success') setTimeout(() => setNotifStatus(null), 2500);
  };

  const handleEmailDigestsToggle = async () => {
    if (isSavingDigests || isSavingSpike) return;
    const v = !emailDigests; setEmailDigests(v);
    setIsSavingDigests(true); setNotifStatus(null);
    try {
      await updatePreferences({ email_digests: v, spike_alerts: spikeAlerts });
      _showNotifStatus('success', 'Preferences saved');
    } catch {
      setEmailDigests(!v);
      _showNotifStatus('error', 'Failed to save. Please try again.');
    } finally { setIsSavingDigests(false); }
  };

  const handleSpikeAlertsToggle = async () => {
    if (isSavingDigests || isSavingSpike) return;
    const v = !spikeAlerts; setSpikeAlerts(v);
    setIsSavingSpike(true); setNotifStatus(null);
    try {
      await updatePreferences({ email_digests: emailDigests, spike_alerts: v });
      _showNotifStatus('success', 'Preferences saved');
    } catch {
      setSpikeAlerts(!v);
      _showNotifStatus('error', 'Failed to save. Please try again.');
    } finally { setIsSavingSpike(false); }
  };

  const inputClass = 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-secondary';
  const btnPrimary = 'w-full py-2.5 bg-brand-primary hover:bg-brand-secondary text-white font-bold rounded-lg transition-colors';
  const btnSecondary = 'w-full py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-brand-primary dark:text-slate-200 font-bold rounded-lg transition-colors mt-2';

  return (
    <div className="animate-in fade-in duration-500 w-full mb-8">
      <div className="flex flex-col mb-8">
        <h1 className="text-4xl font-extrabold text-brand-primary dark:text-white mb-2 tracking-tight">Settings</h1>
      </div>

      <div className="flex flex-col gap-6">
        {/* ACCOUNT */}
        <div>
          <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 mb-3 uppercase tracking-wider">Account</h2>
          <div className="flex flex-col">
            <div
              onClick={() => setActiveModal('profile')}
              className="group flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors rounded-t-xl"
            >
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary dark:text-brand-secondary font-bold text-lg">
                  {getInitials(user?.name || user?.username || '?')}
                </div>
                <div>
                  <h4 className="text-base font-bold text-brand-primary dark:text-white group-hover:text-brand-secondary transition-colors">{user?.name || user?.username || 'User'}</h4>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{user?.email || ''}</p>
                </div>
              </div>
              <ChevronRight size={20} className="text-slate-400 group-hover:text-brand-secondary transition-colors" />
            </div>
            <SettingsItem icon={Lock} title="Change password" description="Update your login password" onClick={() => setActiveModal('password')} isBottom={true} />
          </div>
        </div>

        <SettingsItem icon={Shield} title="Privacy and security" description="Two-Factor Authentication" onClick={() => setActiveModal('privacy')} isTop={true} isBottom={true} />
        <SettingsItem icon={Bell} title="Notifications" description="Alerts, digests, and spike notifications" onClick={() => setActiveModal('notifications')} isTop={true} isBottom={true} />

        <SettingsItem icon={Info} title="About" description="v1.0 — Bilingual (SO-EN) Trend Detection" onClick={() => setActiveModal('about')} isTop={true} isBottom={true} />
      </div>

      {/* MODALS */}
      <Modal isOpen={activeModal === 'profile'} onClose={closeModal} title="User Profile">
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center p-6 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800">
            <div className="flex items-center justify-center w-20 h-20 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary dark:text-brand-secondary font-bold text-3xl mb-4">
              {getInitials(user?.name || user?.username || '?')}
            </div>
            <h3 className="text-xl font-bold text-brand-primary dark:text-white">{user?.name || user?.username || 'User'}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">{user?.email || ''}</p>
          </div>
          <button onClick={closeModal} className={btnPrimary}>Done</button>
        </div>
      </Modal>


      <Modal isOpen={activeModal === 'password'} onClose={closeModal} title="Change Password">
        {passwordSuccess ? (
          <div className="flex flex-col items-center justify-center p-8 space-y-4 text-center animate-in zoom-in-95 duration-300">
            <CheckCircle size={48} className="text-brand-secondary" />
            <h3 className="text-lg font-bold text-brand-primary dark:text-white">Password Updated</h3>
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
              <input type="password" required minLength={6} value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className={inputClass} placeholder="••••••••" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">New Password</label>
              <input type="password" required minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputClass} placeholder="••••••••" />
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">At least 8 characters, including a letter and a number.</p>
            </div>
            <button type="submit" disabled={isSubmitting} className={`${btnPrimary} disabled:opacity-70 disabled:cursor-not-allowed`}>
              {isSubmitting ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        )}
      </Modal>

      <Modal isOpen={activeModal === 'privacy'} onClose={closeModal} title="Privacy & Security">
        <div className="space-y-4">
          <div
            onClick={!show2FAInput && !isSending2FA && !confirm2FADisable ? handleToggle2FA : undefined}
            className={`p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center transition-colors ${!show2FAInput && !isSending2FA && !confirm2FADisable ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50' : 'opacity-80'}`}
          >
            <div>
              <h4 className="text-sm font-bold text-brand-primary dark:text-white">Two-Factor Authentication</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                {isSending2FA
                  ? <><Loader2 size={11} className="animate-spin" /> Sending code to email...</>
                  : twoFactor ? 'Enabled — click to disable' : 'Add an extra layer of security'}
              </p>
            </div>
            <Toggle enabled={twoFactor} />
          </div>

          {/* Rendered outside the code panel so a send failure is never silent. */}
          {twoFAError && !show2FAInput && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs rounded-lg font-bold text-center">
              {twoFAError}
            </div>
          )}

          {confirm2FADisable && (
            <form onSubmit={handleConfirmDisable2FA} className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg animate-in slide-in-from-top-2 duration-200">
              <h4 className="text-sm font-bold text-red-700 dark:text-red-400 mb-1">Disable 2FA?</h4>
              <p className="text-xs text-red-600 dark:text-red-400 mb-3">
                Your account will be less secure without two-factor authentication.
                {disableMode === 'code'
                  ? ' Enter the 6-digit code we just emailed you.'
                  : ' Confirm your password to continue.'}
              </p>
              {disableError && (
                <div className="mb-3 p-2 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 text-xs rounded border border-red-300 dark:border-red-800 font-bold">{disableError}</div>
              )}

              {disableMode === 'code' ? (
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  autoFocus
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  maxLength={6}
                  className={inputClass + ' mb-3 text-center font-mono tracking-widest'}
                  required
                />
              ) : (
                <input
                  type="password"
                  autoFocus
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  placeholder="Current password"
                  className={inputClass + ' mb-3'}
                  required
                />
              )}

              <div className="flex gap-2">
                <button type="button" onClick={() => { setConfirm2FADisable(false); setDisablePassword(''); setDisableCode(''); setDisableError(''); setDisableMode('password'); }} className="flex-1 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">Cancel</button>
                <button type="submit" disabled={isDisabling || (disableMode === 'code' ? disableCode.length < 6 : !disablePassword)} className="flex-1 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-xs font-bold rounded-lg transition-colors">
                  {isDisabling ? 'Disabling...' : 'Disable'}
                </button>
              </div>

              {disableMode === 'password' && (
                <button
                  type="button"
                  onClick={handleSwitchToCodeDisable}
                  disabled={isSendingDisableCode}
                  className="w-full mt-3 text-xs font-bold text-red-700 dark:text-red-400 hover:underline disabled:opacity-60"
                >
                  {isSendingDisableCode
                    ? 'Sending code...'
                    : 'Signed in with Google? Use an email code instead'}
                </button>
              )}
            </form>
          )}

          {show2FAInput && (
            <div className="p-4 bg-brand-primary/5 dark:bg-brand-primary/10 border border-brand-primary/20 dark:border-brand-primary/30 rounded-lg animate-in slide-in-from-top-2 duration-300">
              <h4 className="text-sm font-bold text-brand-primary dark:text-brand-secondary mb-2">Verify Email Code</h4>
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-3">We've sent a 6-digit code to your email. Enter it below to enable 2FA.</p>
              {twoFANotice && (
                <div className="mb-3 p-2 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 text-xs rounded border border-amber-200 dark:border-amber-800">{twoFANotice}</div>
              )}
              {twoFAError && (
                <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs rounded border border-red-200 dark:border-red-800 font-bold">{twoFAError}</div>
              )}
              <form onSubmit={handleVerify2FA} className="flex gap-2">
                <input type="text" inputMode="numeric" pattern="[0-9]*" value={twoFACode} onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" maxLength={6} className={inputClass + ' flex-1 tracking-widest text-center font-mono'} required />
                <button type="submit" disabled={isVerifying2FA || twoFACode.length < 6} className="px-4 py-2 bg-brand-primary hover:bg-brand-secondary disabled:opacity-70 text-white font-bold text-sm rounded-lg transition-colors">
                  {isVerifying2FA ? '...' : 'Verify'}
                </button>
              </form>
            </div>
          )}
          <button onClick={closeModal} className={btnSecondary}>Done</button>
        </div>
      </Modal>

      <Modal isOpen={activeModal === 'notifications'} onClose={closeModal} title="Notifications">
        <div className="space-y-4">
          {notifStatus && (
            <div className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold animate-in fade-in duration-200 ${
              notifStatus.type === 'success'
                ? 'bg-brand-secondary/10 text-brand-secondary border border-brand-secondary/20'
                : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800'
            }`}>
              {notifStatus.type === 'success'
                ? <CheckCircle size={15} />
                : <X size={15} />}
              {notifStatus.msg}
            </div>
          )}
          {[
            { label: 'Email Digests', desc: 'Daily summary of trending topics', val: emailDigests, toggle: handleEmailDigestsToggle, saving: isSavingDigests },
            { label: 'Spike Alerts', desc: 'Notify me on sudden topic spikes', val: spikeAlerts, toggle: handleSpikeAlertsToggle, saving: isSavingSpike },
          ].map(({ label, desc, val, toggle, saving }) => (
            <div
              key={label}
              onClick={toggle}
              className={`p-4 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg flex justify-between items-center transition-colors
                ${saving ? 'opacity-70 cursor-wait' : 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50'}`}
            >
              <div>
                <h4 className="text-sm font-bold text-brand-primary dark:text-white">{label}</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  {saving ? <><Loader2 size={11} className="animate-spin" /> Saving...</> : desc}
                </p>
              </div>
              <Toggle enabled={val} />
            </div>
          ))}
          <button onClick={closeModal} className={btnSecondary}>Done</button>
        </div>
      </Modal>


      <Modal isOpen={activeModal === 'about'} onClose={closeModal} title="About Vision Tech">
        <div className="space-y-4 flex flex-col items-center text-center p-4">
          <div className="w-16 h-16 bg-brand-primary rounded-xl flex items-center justify-center shadow-lg shadow-brand-primary/30 mb-2">
            <Shield size={32} className="text-white" />
          </div>
          <h3 className="text-xl font-bold text-brand-primary dark:text-white">Bilingual Trend Detection</h3>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">v1.0.0 — Final Year Project 2026</p>
          <div className="w-full h-px bg-slate-200 dark:bg-slate-800 my-2" />
          <div className="text-sm text-slate-600 dark:text-slate-300 space-y-3 text-left w-full bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
            {[
              { label: 'Developers', value: 'Vision Tech Team' },
              { label: 'System', value: 'DESIGN AND IMPLEMENTATION OF A REAL-TIME BILINGUAL (SOMALI-ENGLISH) TRENDING TOPIC DETECTION SYSTEM FOR TWITTER (X) USING UNSUPERVISED TOPIC MODELING.' },
              { label: 'Institution', value: 'Jamhuriya University of Science and Technology (JUST)' },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1">{label}</p>
                <p className="font-medium text-brand-primary dark:text-white">{value}</p>
              </div>
            ))}
          </div>
          <div className="w-full h-px bg-slate-200 dark:bg-slate-800 my-2" />
          <p className="text-xs text-slate-500 dark:text-slate-400">© 2026 Vision Tech Group 102. All rights reserved.</p>
        </div>
      </Modal>
    </div>
  );
};

export default Setting;
