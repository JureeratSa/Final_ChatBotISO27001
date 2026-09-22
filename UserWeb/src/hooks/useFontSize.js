import { useState, useEffect } from 'react';

// สถานะขนาดฟอนต์ + ปรับปรุงขนาดฟอนต์บนระดับ HTML
export function useFontSize() {
  const [fontSize, setFontSize] = useState(() => {
    const saved = localStorage.getItem('tuh_font_size');
    return saved || 'normal';
  });

  useEffect(() => {
    localStorage.setItem('tuh_font_size', fontSize);
    if (fontSize === 'large') {
      document.documentElement.style.fontSize = '19px';
    } else if (fontSize === 'xl') {
      document.documentElement.style.fontSize = '22px';
    } else {
      // 'normal'
      document.documentElement.style.fontSize = '16px';
    }
  }, [fontSize]);

  return { fontSize, setFontSize };
}
