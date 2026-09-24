/**
 * TUH Chatbot AI — useUserIp Custom Hook
 * ดึง IP Address ของเครื่องผู้ใช้งานผ่าน API '/api/ip':
 * 1. ทำงานแบบ Fire-and-forget ตอน component mount
 * 2. นำ IP ที่ได้ไปแสดงผลบน Topbar สำหรับการตรวจสอบและการติดต่อแจ้งปัญหา
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

export function useUserIp() {
  // ค่า IP เริ่มต้นกรณีรอผลหรือเกิดข้อผิดพลาด
  const [userIp, setUserIp] = useState('127.0.0.1');

  useEffect(() => {
    // ยิงคำขอไปยัง Backend เพื่อตรวจจับ Remote IP ของ Client
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

