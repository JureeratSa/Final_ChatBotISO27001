/**
 * TUH Chatbot AI — useClock Custom Hook
 * จัดการนาฬิกา Real-time (อัปเดตทุก 1 วินาที) สำหรับใช้คำนวณเวลาที่เหลือก่อน Session แชทหมดอายุ (Auto-expire 1 ชั่วโมง)
 */
import { useState, useEffect } from 'react';

export function useClock() {
  // เก็บ timestamp ปัจจุบัน (มิลลิวินาที)
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    // ตั้งเวลา interval ให้ดึง Date.now() ทุก 1,000 มิลลิวินาที (1 วินาที)
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    // Cleanup interval เมื่อ unmount เพื่อป้องกัน memory leak
    return () => clearInterval(timer);
  }, []);

  return currentTime;
}

