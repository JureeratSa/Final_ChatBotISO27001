/**
 * TUH Chatbot AI — useWelcomeSettings Custom Hook
 * โหลดการตั้งค่าระบบจาก Backend ('/api/admin/settings'):
 * 1. ข้อความต้อนรับหน้าหลัก (welcome_message)
 * 2. ข้อความทักทายเมื่อเปิดห้องแชทใหม่ (chat_greeting)
 * 3. รายการคำถามที่พบบ่อย (predefined_faqs)
 * 4. Patch ข้อมูลที่โหลดได้เข้าสู่ Session เริ่มต้นทันทีแบบ Reactive
 */
import { useState, useEffect } from 'react';
import { API_URL, DEFAULT_WELCOME_MESSAGE, DEFAULT_GREETING } from '../utils/chatUtils';

export function useWelcomeSettings({ setSessions }) {
  // ข้อความต้อนรับบนหน้าแรก (Welcome Screen)
  const [welcomeMessage, setWelcomeMessage] = useState(() => {
    return localStorage.getItem('tuh_welcome_message') || DEFAULT_WELCOME_MESSAGE;
  });

  // ข้อความทักทายเริ่มต้นของบอทในห้องแชทใหม่
  const [chatGreeting, setChatGreeting] = useState(() => {
    return localStorage.getItem('tuh_chat_greeting') || DEFAULT_GREETING;
  });

  // รายการคำถามที่พบบ่อย (FAQs)
  const [faqsList, setFaqsList] = useState([]);

  // ดึงข้อมูลการตั้งค่าจาก API ตอนเริ่มต้นระบบ
  useEffect(() => {
    fetch(API_URL + '/api/admin/settings')
      .then(r => r.json())
      .then(data => {
        if (data) {
          // อัปเดตข้อความต้อนรับหน้าแรก
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

          // อัปเดตข้อความทักทายของห้องแชท
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

          // อัปเดตรายการคำถามที่พบบ่อย (FAQs)
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

