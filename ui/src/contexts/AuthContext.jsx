import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      // In a real app, verify token with backend here
      // For now, we'll just mock a user if token exists
      setUser({ username: 'Admin', email: 'admin@visiontech.com' });
    }
    setIsLoading(false);
  }, [token]);

  const login = async (email, password) => {
    // Mock login for demo purposes. Replace with actual API call.
    // const response = await axios.post('http://localhost:8000/auth/login', { email, password });
    // const { auth_token, user_data } = response.data;
    const mockToken = 'mock-jwt-token-12345';
    const mockUser = { username: 'Admin', email };
    
    setToken(mockToken);
    setUser(mockUser);
    localStorage.setItem('token', mockToken);
  };

  const signup = async (username, email, password) => {
    // Mock signup
    const mockToken = 'mock-jwt-token-67890';
    const mockUser = { username, email };
    
    setToken(mockToken);
    setUser(mockUser);
    localStorage.setItem('token', mockToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, isLoading, login, signup, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};
