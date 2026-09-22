import { useState, useEffect } from 'react';

// แสดงหรือซ่อนคำถามที่พบบ่อย (FAQs) โดยอัตโนมัติตามข้อความในแชทปัจจุบัน เมื่อ activeSessionId เปลี่ยน
// หมายเหตุ (จงใจ): dependency array มีแค่ [activeSessionId] เท่านั้น แม้จะอ่าน sessions ด้านในผ่าน .find
// ก็ตาม — ห้ามเพิ่ม sessions/messages เข้า deps เพราะต้องการให้ FAQ re-evaluate เฉพาะตอนสลับ session
// เท่านั้น ไม่ใช่ทุกครั้งที่มีข้อความใหม่ในเซสชันเดิม
export function useFaqVisibility({ sessions, activeSessionId }) {
  const [showFaqs, setShowFaqs] = useState(true);

  useEffect(() => {
    const session = sessions.find(s => s.id === activeSessionId);
    if (session) {
      setShowFaqs(session.messages.length <= 1);
    }
  }, [activeSessionId]);

  return { showFaqs, setShowFaqs };
}
