/**
 * TUH Chatbot AI v2 — Admin Login Page
 * คง design เดิม: glassmorphism, gradient background
 */
import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

const AdminLogin = ({ onLoginSuccess }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(username, password);
      onLoginSuccess?.();
    } catch (err) {
      setError(err.response?.data?.detail || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zayg-gradient dark:bg-zayg-gradient flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="glass-panel rounded-3xl p-8 shadow-2xl">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-tuh-gradient-1 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
              <i className="fas fa-shield-alt text-white text-2xl" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              TUH Admin Panel
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              ระบบจัดการแชทบอท โรงพยาบาลธรรมศาสตร์ฯ
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
              <i className="fas fa-exclamation-circle mr-2" />
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                ชื่อผู้ใช้
              </label>
              <div className="relative">
                <i className="fas fa-user absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm" />
                <input
                  id="username-input"
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full glass-input rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 text-slate-800 dark:text-slate-100"
                  placeholder="ชื่อผู้ใช้"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                รหัสผ่าน
              </label>
              <div className="relative">
                <i className="fas fa-lock absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm" />
                <input
                  id="password-input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full glass-input rounded-xl pl-10 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 text-slate-800 dark:text-slate-100"
                  placeholder="รหัสผ่าน"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'} text-sm`} />
                </button>
              </div>
            </div>

            <button
              id="login-button"
              type="submit"
              disabled={isLoading}
              className="w-full bg-tuh-gradient-1 text-white py-3 rounded-xl font-semibold shadow-md hover:shadow-lg hover:opacity-95 active:scale-[0.98] transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  กำลังเข้าสู่ระบบ...
                </span>
              ) : 'เข้าสู่ระบบ'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
