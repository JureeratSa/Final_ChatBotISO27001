import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

// ประกาศที่กำลังเปิดใช้งานอยู่ — โหลดจาก /api/announcements/active ตอน mount
// (แยกออกมาจาก effect รวม 3 fetch เดิมของ App.jsx — เป็น fire-and-forget GET ที่เป็นอิสระจาก 2 fetch อื่น)
export function useAnnouncements() {
  const [activeAnnouncements, setActiveAnnouncements] = useState([]);
  const [showAnnModal, setShowAnnModal] = useState(false);

  const handleCloseAnnModal = () => {
    setShowAnnModal(false);
    sessionStorage.setItem('tuh_announcements_seen', 'true');
  };

  // โหลดประกาศที่กำลังเปิดใช้งานอยู่
  useEffect(() => {
    fetch(API_URL + '/api/announcements/active')
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          setActiveAnnouncements(data);
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
