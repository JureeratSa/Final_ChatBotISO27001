import { useState, useEffect } from 'react';

/**
 * useAuth — สถานะ login/logout, adminUser, และ authenticated fetch wrapper (แนบ JWT
 * token + auto-logout เมื่อโดน 401) รวมถึง auto-logout เมื่อไม่มีการใช้งานเกิน 10 นาที
 * แยกออกมาจาก App.jsx เดิม
 *
 * fetchWithAuth ถูกคืนกลับมาในชื่อ `fetch` (shadow ชื่อ global fetch โดยตั้งใจ เหมือนโค้ดเดิม)
 * เพื่อให้ hook อื่นๆ ที่รับพารามิเตอร์นี้ไปเรียกใช้ ไม่ต้องแก้ไขชื่อฟังก์ชันภายใน handler เดิมเลย
 */
export function useAuth(API_URL, showSuccess, showError, setActiveTab) {
  // Authentication State
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem('tuh_admin_token') !== null;
  });
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Profile data (adminUser lives here because it's set at login time and read by
  // role-gated routing/UI throughout the app)
  const [adminUser, setAdminUser] = useState(() => {
    const saved = localStorage.getItem('tuh_admin_user');
    return saved ? JSON.parse(saved) : { name: 'แอดมิน สารสนเทศ', role: 'System Administrator', email: 'it@tuh.ac.th' };
  });

  // Password Visibility Toggle State (login form only)
  const [showPassword, setShowPassword] = useState(false);

  let logoutRef = () => { };

  const fetch = (url, options = {}) => {
    const urlStr = typeof url === 'string' ? url : (url.url || '');
    const isLogin = urlStr.includes('/api/admin/login') || urlStr.includes('/api/auth/login');
    const isFeedbackOrUnansweredSubmit = urlStr.includes('/api/admin/feedback/submit') || urlStr.includes('/api/admin/unanswered/submit');
    const isAdmin = urlStr.includes('/api/admin/') || urlStr.includes('/api/auth/');

    if (isAdmin && !isLogin && !isFeedbackOrUnansweredSubmit) {
      const token = localStorage.getItem('tuh_admin_token');
      if (token) {
        options.headers = {
          ...options.headers,
          'Authorization': `Bearer ${token}`
        };
      }
    }

    return window.fetch(url, options).then(res => {
      if (res.status === 401 && isAdmin && !isLogin && !isFeedbackOrUnansweredSubmit) {
        logoutRef();
      }
      return res;
    });
  };

  // Actions
  const handleLogin = (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    fetch(API_URL + '/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
      .then(res => {
        if (!res.ok) throw new Error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง");
        return res.json();
      })
      .then(data => {
        localStorage.setItem('tuh_admin_token', data.token);
        localStorage.setItem('tuh_admin_user', JSON.stringify(data));
        setAdminUser(data);
        setIsLoggedIn(true);
        showSuccess("เข้าสู่ระบบเรียบร้อยแล้ว");
      })
      .catch(err => {
        setLoginError(err.message);
      })
      .finally(() => {
        setLoginLoading(false);
      });
  };

  const handleLogout = () => {
    localStorage.removeItem('tuh_admin_token');
    localStorage.removeItem('tuh_admin_user');
    localStorage.removeItem('tuh_admin_active_tab');
    setActiveTab('dashboard');
    setUsername('');
    setPassword('');
    setIsLoggedIn(false);
  };
  logoutRef = handleLogout;

  // Auto logout after 10 minutes of inactivity
  useEffect(() => {
    if (!isLoggedIn) return;

    let timeoutId;

    const resetTimer = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        handleLogout();
        showError("เซสชันหมดอายุเนื่องจากไม่มีการใช้งานเกิน 10 นาที");
      }, 10 * 60 * 1000);
    };

    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(event => {
      window.addEventListener(event, resetTimer);
    });

    resetTimer();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      events.forEach(event => {
        window.removeEventListener(event, resetTimer);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  return {
    fetch,
    isLoggedIn,
    setIsLoggedIn,
    username,
    setUsername,
    password,
    setPassword,
    loginError,
    loginLoading,
    adminUser,
    setAdminUser,
    showPassword,
    setShowPassword,
    handleLogin,
    handleLogout,
  };
}
