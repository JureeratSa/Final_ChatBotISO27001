/**
 * TUH Chatbot AI — useFaqVisibility Custom Hook
 * ควบคุมการแสดงผล/ซ่อนปุ่มรายการคำถามที่พบบ่อย (FAQs List):
 * 1. ตรวจสอบว่าแชทปัจจุบันเป็นห้องว่าง (messages <= 1) หรือไม่
 * 2. เมื่อผู้ใช้สลับ Session (activeSessionId เปลี่ยน) จะคำนวณการแสดงผลใหม่
 * 3. ซ่อนอัตโนมัติเมื่อผู้ใช้เริ่มพิมพ์ข้อความแรก
 */
import { useState, useEffect } from 'react';

export function useFaqVisibility({ sessions, activeSessionId }) {
  const [showFaqs, setShowFaqs] = useState(true);

  // ตรวจสอบสถานะการเปิด/ปิด FAQ เฉพาะเมื่อสลับ activeSessionId
  useEffect(() => {
    const session = sessions.find(s => s.id === activeSessionId);
    if (session) {
      // แสดง FAQ เฉพาะเมื่อห้องแชทมีข้อความต้อนรับเพียง 1 ข้อความ (ยังไม่เริ่มคุย)
      setShowFaqs(session.messages.length <= 1);
    }
  }, [activeSessionId]);

  return { showFaqs, setShowFaqs };
}

