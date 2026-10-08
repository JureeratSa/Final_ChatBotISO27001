import { useState, useEffect } from 'react';

/**
 * useTheme — จัดการสถานะ dark mode ของ AdminWeb ทั้งหมด (toggle + sync กับ <html> class
 * + persist ลง localStorage) แยกออกมาจาก App.jsx เดิม
 */
export function useTheme() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_admin_theme');
    return saved === 'dark';
  });

  // Sync Theme with HTML Class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tuh_admin_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tuh_admin_theme', 'light');
    }
  }, [isDarkMode]);

  return { isDarkMode, setIsDarkMode };
}
