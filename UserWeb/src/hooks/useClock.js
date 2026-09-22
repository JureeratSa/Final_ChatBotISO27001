import { useState, useEffect } from 'react';

// สถานะเวลาปัจจุบันสำหรับการอัปเดตการนับถอยหลังแบบเรียลไทม์
export function useClock() {
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return currentTime;
}
