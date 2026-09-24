/**
 * TUH Chatbot AI — useAnnouncements Custom Hook
 * จัดการการดึงและแสดงผลกล่องข้อความประกาศข่าวสาร (Announcements Popup):
 * 1. ดึงประกาศที่กำลัง Active ผ่าน API '/api/announcements/active' ตอน mount
 * 2. ตรวจสอบ sessionStorage ('tuh_announcements_seen') เพื่อแสดง Popup เฉพาะครั้งแรกที่เข้าใช้งาน
 * 3. บันทึกสถานะการปิด Popup เพื่อไม่ให้เด้งซ้ำซ้อนใน session เดียวกัน
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

export function useAnnouncements() {
  const [activeAnnouncements, setActiveAnnouncements] = useState([]);
  const [showAnnModal, setShowAnnModal] = useState(false);

  // ฟังก์ชันปิด Modal ประกาศ และบันทึกว่าผู้ใช้เห็นประกาศแล้วใน sessionStorage
  const handleCloseAnnModal = () => {
    setShowAnnModal(false);
    sessionStorage.setItem('tuh_announcements_seen', 'true');
  };

  // โหลดรายการประกาศที่ Active เมื่อเริ่มต้นระบบ
  useEffect(() => {
    fetch(API_URL + '/api/announcements/active')
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          setActiveAnnouncements(data);
          // ตรวจสอบว่าเคยเปิดอ่านประกาศไปแล้วในแท็บนี้หรือไม่
          const hasSeen = sessionStorage.getItem('tuh_announcements_seen');
          if (hasSeen !== 'true') {
            setShowAnnModal(true);
          }
        }
      })
      .catch(err => console.error("Error fetching active announcements:", err));
  }, []);

  return { activeAnnouncements, showAnnModal, handleCloseAnnModal };
}

