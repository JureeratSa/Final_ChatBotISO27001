/**
 * TUH Chatbot AI v2 — Auth Context
 * จัดการ JWT Token, Login State, Auto-refresh
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const logout = useCallback(() => {
    localStorage.removeItem('tuh_access_token');
    localStorage.removeItem('tuh_refresh_token');
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const login = useCallback(async (username, password) => {
    const { data } = await authAPI.login(username, password);
    localStorage.setItem('tuh_access_token', data.access_token);
    localStorage.setItem('tuh_refresh_token', data.refresh_token);
    setUser({
      username: data.username,
      displayName: data.display_name,
      role: data.role,
    });
    setIsAuthenticated(true);
    return data;
  }, []);

  // ตรวจสอบ token เมื่อ app โหลด
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('tuh_access_token');
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const { data } = await authAPI.getMe();
        setUser({
          username: data.username,
          displayName: data.display_name,
          role: data.role,
        });
        setIsAuthenticated(true);
      } catch {
        logout();
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
