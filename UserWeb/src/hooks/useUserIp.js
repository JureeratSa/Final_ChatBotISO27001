import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

// IP ของผู้ใช้ — โหลดจาก /api/ip ตอน mount
// (แยกออกมาจาก effect รวม 3 fetch เดิมของ App.jsx — เป็น fire-and-forget GET ที่เป็นอิสระจาก 2 fetch อื่น)
export function useUserIp() {
  const [userIp, setUserIp] = useState('127.0.0.1');

  useEffect(() => {
    fetch(API_URL + '/api/ip')
      .then(res => res.json())
      .then(data => {
        if (data && data.ip) {
          setUserIp(data.ip);
        }
      })
      .catch(err => console.error("Error fetching client IP:", err));
  }, []);

  return userIp;
}
