import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginUser, verifyLogin2FA, signupUser, loginWithGoogle, changeUserPassword, get2FAStatus, request2FACode, verify2FACode, disable2FA, getPreferences, updatePreferences } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

const decodeJWT = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      const decoded = decodeJWT(token);
      if (decoded && decoded.sub) {
        const username = decoded.sub;
        const name = username.includes('@') ? username.split('@')[0] : username;
        setUser({ email: username, name: name });
      } else {
        setUser({ email: 'user@visiontech.com', name: 'User' });
      }
    }
    setIsLoading(false);
  }, [token]);

  // Stores a freshly issued session token and derives the display user from it.
  const establishSession = (accessToken, fallbackEmail) => {
    setToken(accessToken);
    const decoded = decodeJWT(accessToken);
    const username = decoded?.sub || fallbackEmail;
    const name = username.includes('@') ? username.split('@')[0] : username;
    setUser({ email: username, name });
    localStorage.setItem('token', accessToken);
  };

  // Returns { success } on a completed login, or { requires2FA, challengeToken }
  // when the account has 2FA on — no session exists until the code is verified.
  const login = async (email, password) => {
    try {
      const data = await loginUser(email, password);
      if (data.requires_2fa) {
        return {
          success: false,
          requires2FA: true,
          challengeToken: data.challenge_token,
          devCode: data.dev_code || null,
        };
      }
      establishSession(data.access_token, email);
      return { success: true };
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const completeLogin2FA = async (challengeToken, code) => {
    try {
      const data = await verifyLogin2FA(challengeToken, code);
      establishSession(data.access_token, '');
      return { success: true };
    } catch (error) {
      console.error("2FA verification failed:", error);
      throw error;
    }
  };

  const signup = async (username, email, password) => {
    try {
      await signupUser(username, email, password);
      return { success: true };
    } catch (error) {
      console.error("Signup failed:", error);
      throw error;
    }
  };

  const googleLogin = async (credential) => {
    try {
      const data = await loginWithGoogle(credential);
      // Google sign-in is subject to the same 2FA gate as password login.
      if (data.requires_2fa) {
        return {
          success: false,
          requires2FA: true,
          challengeToken: data.challenge_token,
          devCode: data.dev_code || null,
        };
      }
      establishSession(data.access_token, 'google.auth@visiontech.com');
      return { success: true };
    } catch (error) {
      console.error("Google Auth failed:", error);
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      await changeUserPassword(currentPassword, newPassword);
      return { success: true };
    } catch (error) {
      console.error("Change password failed:", error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ 
      user, token, isAuthenticated: !!token, isLoading, 
      login, completeLogin2FA, signup, googleLogin, logout, setUser, changePassword,
      get2FAStatus, request2FACode, verify2FACode, disable2FA,
      getPreferences, updatePreferences
    }}>
      {children}
    </AuthContext.Provider>
  );
};

