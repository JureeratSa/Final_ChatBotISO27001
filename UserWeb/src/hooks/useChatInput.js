import { useState, useRef, useEffect } from 'react';
import { API_URL, getBotResponse } from '../utils/chatUtils';

// ตรวจ 2-of-3 forced-feedback trigger: เรียกจากทั้ง success branch และ generic-error branch ของ
// handleSendMessage เท่านั้น (2 จุดเท่านั้น) — ตั้งใจไม่เรียกใน AbortError branch เพราะการยกเลิกคำขอ
// ไม่ควรถูกนับเป็นเงื่อนไขเข้าเกณฑ์บังคับกรอกข้อเสนอแนะ
function maybeTriggerForcedFeedback(nextCount, setIsForcedFeedback, setShowFeedback) {
  if (nextCount === 3 && sessionStorage.getItem('tuh_feedback_submitted') !== 'true') {
    setTimeout(() => {
      setIsForcedFeedback(false);
      setShowFeedback(true);
    }, 1000);
  }
}

// สถานะช่องพิมพ์ข้อความ, การพิมพ์ของบอท, ตัวนับคำถาม, refs ที่เกี่ยวข้อง (auto-focus/auto-scroll/abort)
// และ handleSendMessage / handleStopGeneration
export function useChatInput({
  sessions,
  activeSessionId,
  setSessions,
  activeSession,
  faqsList,
  setShowFaqs,
  setIsForcedFeedback,
  setShowFeedback
}) {
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // คำถาม & แสดงความคิดเห็นที่ไม่พอใจ
  const [questionCount, setQuestionCount] = useState(() => {
    const saved = sessionStorage.getItem('tuh_question_count');
    return saved ? parseInt(saved, 10) : 0;
  });

  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Auto-focus input textarea when bot finishes typing
  useEffect(() => {
    if (!isTyping && inputRef.current) {
      const timer = setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isTyping]);

  // เลื่อนลงไปด้านล่างสุดโดยอัตโนมัติ
  useEffect(() => {
    const scrollToBottom = () => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior: 'smooth'
        });
      } else {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    };

    // เลื่อนลงไปด้านล่างทันที
    scrollToBottom();

    // เลื่อนลงอีกครั้งหลังจากผ่านไปช่วงสั้น ๆ เพื่อให้แน่ใจว่า DOM ถูกเรนเดอร์,
    // การอัปเดตเค้าโครง และแอนิเมชันการเปลี่ยนสถานะของข้อความฟองสบู่ทำงานเสร็จสิ้น
    const timer1 = setTimeout(scrollToBottom, 100);
    const timer2 = setTimeout(scrollToBottom, 300);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [sessions, activeSessionId, isTyping]);

  // ยกเลิกการหาคำตอบ
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
  };

  // ประมวลผลและส่งข้อความจากผู้ใช้
  const handleSendMessage = (text) => {
    if (!text.trim() || isTyping) return;

    // หากไม่ใช่แชทล่าสุด จะส่งข้อความไม่ได้
    // (จงใจคำนวณ isActiveSessionLatest ซ้ำในนี้แม้จะมีค่าที่ derived จาก useChatSessions อยู่แล้วก็ตาม
    // — เป็นการซ้ำซ้อนเล็กน้อยที่มีอยู่แล้วในโค้ดต้นฉบับ ให้คงไว้ตามเดิม ไม่ทำการ dedupe)
    const isActiveSessionLatest = activeSessionId === sessions[0]?.id;
    if (!isActiveSessionLatest) return;

    localStorage.setItem('tuh_last_chat_time', Date.now().toString());

    const nextCount = questionCount + 1;
    setQuestionCount(nextCount);
    sessionStorage.setItem('tuh_question_count', nextCount.toString());

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
    };

    // คัดแยกประวัติการสนทนาล่าสุด (ไม่เกิน 2 รอบ / 4 ข้อความ)
    const sessionMessages = activeSession.messages || [];
    const startIndex = (sessionMessages.length > 0 && sessionMessages[0].sender === 'bot') ? 1 : 0;
    const candidates = sessionMessages.slice(startIndex);
    const recentHistory = candidates.slice(-4).map(m => ({
      sender: m.sender,
      text: m.text
    }));

    // อัปเดตข้อความในเซสชันที่ใช้งาน
    let updatedSessions = sessions.map(s => {
      if (s.id === activeSessionId) {
        // อัปเดตชื่อเซสชันตามข้อความแรกของผู้ใช้ หากชื่อเดิมเป็นชื่อเริ่มต้น
        let newTitle = s.title;
        if (s.title.startsWith('บทสนทนาใหม่ #')) {
          newTitle = text.length > 25 ? text.substring(0, 25) + '...' : text;
        }
        return {
          ...s,
          title: newTitle,
          messages: [...s.messages, userMessage]
        };
      }
      return s;
    });

    // หมายเหตุ (จงใจ, ห้าม "แก้ให้สม่ำเสมอ"): การอัปเดตนี้ใช้ closure ของ `sessions` ตรงๆ ได้อย่างปลอดภัย
    // เพราะรันแบบ synchronous ก่อนจะมี await ใดๆ เกิดขึ้น ในขณะที่ setSessions ทั้ง 3 จุดด้านล่างใน
    // .then()/.catch() ต้องใช้ functional form (prevSessions => ...) เพราะรันหลัง async gap ที่ sessions
    // อาจถูกเปลี่ยนแปลงไปแล้วจากตอนที่ปิด closure ไว้
    setSessions(updatedSessions);
    setInputValue('');
    setShowFaqs(false);
    setIsTyping(true);

    // สร้าง AbortController ใหม่สำหรับการค้นหานี้
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // เรียก API ค้นหาแบบผสม (ChromaDB + BM25) ของ Python
    fetch(API_URL + '/api/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({
        query: text,
        top_k: 2,
        history: recentHistory
      }),
      signal: controller.signal
    })
      .then(response => {
        if (!response.ok) throw new Error("HTTP error " + response.status);
        return response.json();
      })
      .then(data => {
        abortControllerRef.current = null;
        //ใช้คำตอบ AI ที่สร้างจากส่วนหลังบ้านหากมี
        let botResponseText = data.answer || getBotResponse(text, faqsList);
        botResponseText = botResponseText.replaceAll("__API_URL__", API_URL);

        const botMessage = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: botResponseText,
          citations: data.citations || [],
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        };

        setSessions(prevSessions => prevSessions.map(s => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, botMessage]
            };
          }
          return s;
        }));
        localStorage.setItem('tuh_last_chat_time', Date.now().toString());
        setIsTyping(false);

        // กำหนดให้แสดงฟอร์มข้อเสนอแนะหลังจากข้อความจากบอทข้อที่ 3 หากยังไม่มีการส่งข้อเสนอแนะ
        maybeTriggerForcedFeedback(nextCount, setIsForcedFeedback, setShowFeedback);
      })
      .catch(error => {
        if (error.name === 'AbortError') {
          console.log("API Search request aborted.");
          const botMessage = {
            id: `bot-${Date.now()}`,
            sender: 'bot',
            text: `ขาหมูได้ทำการยกเลิกการหาคำตอบแล้วครับ`,
            timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
          };

          setSessions(prevSessions => prevSessions.map(s => {
            if (s.id === activeSessionId) {
              return {
                ...s,
                messages: [...s.messages, botMessage]
              };
            }
            return s;
          }));
          localStorage.setItem('tuh_last_chat_time', Date.now().toString());
          setIsTyping(false);
          // จงใจไม่เรียก maybeTriggerForcedFeedback ที่นี่ — ยกเลิกคำขอไม่ควรถูกนับเข้าเกณฑ์บังคับ
          // กรอกข้อเสนอแนะ (asymmetry เดิมของโค้ดต้นฉบับ)
          return;
        }

        abortControllerRef.current = null;
        console.warn("API Search failed, using static fallback:", error);
        // ใช้ค่าเริ่มต้นแทนหากเกิดข้อผิดพลาด
        const botResponseText = getBotResponse(text, faqsList);
        const botMessage = {
          id: `bot-${Date.now()}`,
          sender: 'bot',
          text: botResponseText,
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        };

        setSessions(prevSessions => prevSessions.map(s => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, botMessage]
            };
          }
          return s;
        }));
        localStorage.setItem('tuh_last_chat_time', Date.now().toString());
        setIsTyping(false);

        // กำหนดให้แสดงฟอร์มข้อเสนอแนะหลังจากข้อความจากบอทข้อที่ 3 หากยังไม่มีการส่งข้อเสนอแนะ
        maybeTriggerForcedFeedback(nextCount, setIsForcedFeedback, setShowFeedback);
      });
  };

  return {
    inputValue, setInputValue,
    isTyping,
    inputRef, chatEndRef, chatContainerRef,
    handleSendMessage, handleStopGeneration
  };
}
