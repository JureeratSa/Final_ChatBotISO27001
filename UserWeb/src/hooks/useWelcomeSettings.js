import { useState, useEffect } from 'react';
import { API_URL, DEFAULT_WELCOME_MESSAGE, DEFAULT_GREETING } from '../utils/chatUtils';

// ข้อความต้อนรับ, คำทักทายในฝั่งแชท และรายการ FAQ ที่กำหนดเอง — โหลดจาก /api/admin/settings ตอน mount
// (แยกออกมาจาก effect รวม 3 fetch เดิมของ App.jsx — เป็น fire-and-forget GET ที่เป็นอิสระจาก 2 fetch
// อื่น จึงแยก effect ได้โดยไม่กระทบพฤติกรรม) ต้องรับ setSessions จาก useChatSessions เข้ามาด้วย เพราะ
// callback ของ fetch นี้ต้อง patch ข้อความต้อนรับ/คำทักทายลงใน session ที่ยังเป็นข้อความเริ่มต้นอยู่
export function useWelcomeSettings({ setSessions }) {
  const [welcomeMessage, setWelcomeMessage] = useState(() => {
    return localStorage.getItem('tuh_welcome_message') || DEFAULT_WELCOME_MESSAGE;
  });

  const [chatGreeting, setChatGreeting] = useState(() => {
    return localStorage.getItem('tuh_chat_greeting') || DEFAULT_GREETING;
  });

  const [faqsList, setFaqsList] = useState([]);

  // โหลดข้อความต้อนรับแบบกำหนดเองและการตั้งค่าเมื่อเริ่มต้นระบบ
  useEffect(() => {
    fetch(API_URL + '/api/admin/settings')
      .then(r => r.json())
      .then(data => {
        if (data) {
          if (data.welcome_message) {
            setWelcomeMessage(data.welcome_message);
            localStorage.setItem('tuh_welcome_message', data.welcome_message);
            setSessions(prev => prev.map(s => {
              if (s.id === 'session-1' && s.messages.length === 1 && s.messages[0].id === 'm1') {
                return {
                  ...s,
                  messages: [{
                    ...s.messages[0],
                    text: data.welcome_message
                  }]
                };
              }
              return s;
            }));
          }
          if (data.chat_greeting) {
            setChatGreeting(data.chat_greeting);
            localStorage.setItem('tuh_chat_greeting', data.chat_greeting);
            setSessions(prev => prev.map(s => {
              if (s.id !== 'session-1' && s.messages.length === 1 && s.messages[0].sender === 'bot' && (s.messages[0].text === DEFAULT_GREETING || s.messages[0].id === 'm1')) {
                return {
                  ...s,
                  messages: [{
                    ...s.messages[0],
                    text: data.chat_greeting
                  }]
                };
              }
              return s;
            }));
          }
          if (data.predefined_faqs && data.predefined_faqs.length > 0) {
            const mappedFaqs = data.predefined_faqs.map(item => ({
              ...item,
              response: item.answer || item.response
            }));
            setFaqsList(mappedFaqs);
          }
        }
      })
      .catch(err => console.warn("Failed to fetch settings from API:", err));
  }, []);

  return { welcomeMessage, chatGreeting, faqsList };
}
