/**
 * TUH Chatbot AI — useTheme Custom Hook
 * จัดการธีมของแอปพลิเคชัน (Light Mode / Dark Mode):
 * 1. อ่านและบันทึกค่าธีมลงใน localStorage ('tuh_theme')
 * 2. ซิงค์ class 'dark' บนแท็ก <html> (document.documentElement)
 * 3. สลับรูปภาพมาสคอต (น้องหมาขาหมู) และรูปอวาตาร์ของบอทให้ตรงตามโหมด
 */
import { useState, useEffect } from 'react';
import dog from '../dog.png';
import dog_light from '../dog_light.png';
import botAvatar from '../bot_avatar.jpg';

export function useTheme() {
  // โหลดค่าธีมเริ่มต้นจาก localStorage ถ้าไม่มีให้ default เป็นโหมดสว่าง (false)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_theme');
    if (saved !== null) {
      return saved === 'dark';
    }
    return false; // ค่าเริ่มต้นเป็น Light Mode
  });

  // สลับรูปภาพมาสคอตและอวาตาร์ตามสถานะธีม
  const currentMascot = isDarkMode ? dog : dog_light;
  const currentBotAvatar = isDarkMode ? botAvatar : dog_light;

  // Effect สำหรับซิงค์คลาส 'dark' เข้ากับแท็ก <html> และบันทึกลง localStorage
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

