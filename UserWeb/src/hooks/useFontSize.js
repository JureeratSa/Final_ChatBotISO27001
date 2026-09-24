/**
 * TUH Chatbot AI — useFontSize Custom Hook
 * จัดการปรับขนาดตัวอักษรของระบบ (Accessibility):
 * 1. รองรับ 3 ระดับ: normal (16px), large (19px), xl (22px)
 * 2. บันทึกและดึงค่าจาก localStorage ('tuh_font_size')
 * 3. ปรับค่า font-size ที่ root HTML element (document.documentElement.style.fontSize)
 */
import { useState, useEffect } from 'react';

export function useFontSize() {
  // โหลดขนาดฟอนต์ที่เคยบันทึกไว้ ถ้าไม่มีให้ใช้ 'normal'
  const [fontSize, setFontSize] = useState(() => {
    const saved = localStorage.getItem('tuh_font_size');
    return saved || 'normal';
  });

  // Effect สำหรับปรับขนาด Base Font Size บนแท็ก <html> และบันทึกลง localStorage
  useEffect(() => {
    localStorage.setItem('tuh_font_size', fontSize);
    if (fontSize === 'large') {
      document.documentElement.style.fontSize = '19px';
    } else if (fontSize === 'xl') {
      document.documentElement.style.fontSize = '22px';
    } else {
      // ค่าปกติ (normal) = 16px
      document.documentElement.style.fontSize = '16px';
    }
  }, [fontSize]);

  return { fontSize, setFontSize };
}

