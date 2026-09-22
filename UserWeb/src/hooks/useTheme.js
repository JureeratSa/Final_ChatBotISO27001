import { useState, useEffect } from 'react';
import dog from '../dog.png';
import dog_light from '../dog_light.png';
import botAvatar from '../bot_avatar.jpg';

// สถานะธีม (โหมดมืด/สว่าง) + มาสคอต/อวาตาร์บอทที่เปลี่ยนตามธีม + ประสานคลาสธีมเข้ากับแท็ก HTML
export function useTheme() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_theme');
    if (saved !== null) {
      return saved === 'dark';
    }
    // ตั้งค่าเริ่มต้นเป็นโหมดสว่าง
    return false;
  });

  const currentMascot = isDarkMode ? dog : dog_light;
  const currentBotAvatar = isDarkMode ? botAvatar : dog_light;

  // ารประสานสถานะธีมเข้ากับคลาสในแท็ก HTML
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tuh_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tuh_theme', 'light');
    }
  }, [isDarkMode]);

  return { isDarkMode, setIsDarkMode, currentMascot, currentBotAvatar };
}
