/**
 * TUH Chatbot AI — useChatInput Custom Hook
 * จัดการกล่องข้อความขาเข้า, การส่งข้อความไปยัง RAG Backend และการควบคุมการพิมพ์ของบอท:
 * 1. ควบคุม State ของช่องพิมพ์ (inputValue, isTyping) และ Auto-scroll แชท
 * 2. handleSendMessage: ตรวจสอบห้องแชทล่าสุด, สร้าง user message, ดึง Recent History 2 รอบ (4 ข้อความ)
 * 3. ส่งคำขอแบบ Abortable (ผ่าน AbortController) ไปยัง '/api/search'
 * 4. Fallback: กรณีต่อเน็ตไม่ได้/API Error ใช้ getBotResponse() ตอบตามคำสำคัญ/FAQ
 * 5. Forced Feedback: นับจำนวนคำถาม (questionCount) และกระตุ้นเปิด Feedback เมื่อถามครบ 3 คำถาม
 * 6. handleStopGeneration: ฟังก์ชันหยุดค้นหาคำตอบระหว่างการประมวลผล
 */
import { useState, useRef, useEffect } from 'react';
import { API_URL, getBotResponse } from '../utils/chatUtils';

/**
 * ตรวจสอบและเปิดกล่องประเมินความพึงพอใจแบบบังคับเมื่อผู้ใช้ถามคำถามครบ 3 ข้อ
 * @param {number} nextCount - จำนวนคำถามสะสม
 * @param {Function} setIsForcedFeedback - ฟังก์ชันเซ็ตโหมดบังคับ
 * @param {Function} setShowFeedback - ฟังก์ชันเปิด Modal
 */
function maybeTriggerForcedFeedback(nextCount, setIsForcedFeedback, setShowFeedback) {
  if (nextCount === 3 && sessionStorage.getItem('tuh_feedback_submitted') !== 'true') {
    setTimeout(() => {
      setIsForcedFeedback(false);
      setShowFeedback(true);
    }, 1000);
  }
}

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

  // ตัวนับจำนวนคำถามที่ผู้ใช้ถามในเซสชันนี้
  const [questionCount, setQuestionCount] = useState(() => {
    const saved = sessionStorage.getItem('tuh_question_count');
    return saved ? parseInt(saved, 10) : 0;
  });

  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const inputRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Auto-focus ช่องพิมพ์ข้อความเมื่อบอทพิมพ์ตอบเสร็จสิ้น
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

  // เลื่อนหน้าจอแชทลงไปด้านล่างสุดโดยอัตโนมัติ (Auto-scroll to bottom)
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

    // เลื่อนซ้ำอีกครั้งหลังจากผ่านไป 100ms และ 300ms เพื่อรองรับช่วงที่ Animation/DOM render เสร็จ
    const timer1 = setTimeout(scrollToBottom, 100);
    const timer2 = setTimeout(scrollToBottom, 300);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [sessions, activeSessionId, isTyping]);

  /**
   * ยกเลิกการค้นหา/สร้างคำตอบของบอทกลางคัน
   */
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsTyping(false);
  };

  /**
   * ส่งข้อความของผู้ใช้ไปยัง API ค้นหา RAG ของ Backend
   * @param {string} text - ข้อความที่ผู้ใช้พิมพ์
   */
  const handleSendMessage = (text) => {
    if (!text.trim() || isTyping) return;

    // อนุญาตให้ส่งข้อความได้เฉพาะใน Session บนสุด (ล่าสุด) เท่านั้น
    const isActiveSessionLatest = activeSessionId === sessions[0]?.id;
    if (!isActiveSessionLatest) return;

    localStorage.setItem('tuh_last_chat_time', Date.now().toString());

    // อัปเดตตัวนับจำนวนคำถาม
    const nextCount = questionCount + 1;
    setQuestionCount(nextCount);
    sessionStorage.setItem('tuh_question_count', nextCount.toString());

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
    };

    // คัดแยกประวัติการสนทนาล่าสุด (ไม่เกิน 2 รอบ / 4 ข้อความ) เพื่อส่งเป็น Multi-turn context
    const sessionMessages = activeSession.messages || [];
    const startIndex = (sessionMessages.length > 0 && sessionMessages[0].sender === 'bot') ? 1 : 0;
    const candidates = sessionMessages.slice(startIndex);
    const recentHistory = candidates.slice(-4).map(m => ({
      sender: m.sender,
      text: m.text
    }));

    // อัปเดตข้อความของผู้ใช้ลงใน State sessions
    let updatedSessions = sessions.map(s => {
      if (s.id === activeSessionId) {
        // อัปเดตชื่อห้องแชทตามข้อความแรก หากชื่อยังเป็นชื่อเริ่มต้น
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

    setSessions(updatedSessions);
    setInputValue('');
    setShowFaqs(false);
    setIsTyping(true);

    // สร้าง AbortController ใหม่สำหรับการยกเลิกคำขอ
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // ส่งคำขอค้นหาแบบ Hybrid (ChromaDB + BM25) ไปยัง Backend API
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
        // ใช้คำตอบที่ Backend ตอบกลับ หรือ Fallback กรณีไม่มี
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

        // ตรวจสอบเงื่อนไขกระตุ้นฟอร์มความพึงพอใจหลังตอบคำถามข้อที่ 3
        maybeTriggerForcedFeedback(nextCount, setIsForcedFeedback, setShowFeedback);
      })
      .catch(error => {
        // กรณีผู้ใช้กดยกเลิกการค้นหา (Abort)
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
          return;
        }

        abortControllerRef.current = null;
        console.warn("API Search failed, using static fallback:", error);
        // กรณีเชื่อมต่อ API ล้มเหลว ใช้ Static Fallback ตอบตามคำสำคัญ
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

        // ตรวจสอบเงื่อนไขกระตุ้นฟอร์มความพึงพอใจ
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

