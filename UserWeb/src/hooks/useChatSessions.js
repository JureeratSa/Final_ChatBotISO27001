/**
 * TUH Chatbot AI — useChatSessions Custom Hook
 * จัดการ Lifecycle และ State ของเซสชันการสนทนาทั้งหมด (Core State Management):
 * 1. computeInitialSessionState: โหลดแชทเดิมจาก localStorage ('tuh_chats'), กรองข้อมูลเก่าเกิน 1 ชั่วโมง (Auto-expire)
 * 2. Auto-expire Effect: ตรวจสอบและลบเซสชันที่หมดอายุ (เกิน 1 ชั่วโมง) ตามรอบนาฬิกา Real-time
 * 3. handleNewChat: สร้างห้องสนทนาใหม่พร้อมข้อความทักทาย (Chat Greeting)
 * 4. handleDeleteSession: ลบห้องสนทนาที่เลือก (ป้องกันการลบห้องปัจจุบันหรือลบจนหมด)
 */
import { useState, useRef, useEffect } from 'react';
import { DEFAULT_WELCOME_MESSAGE, DEFAULT_GREETING } from '../utils/chatUtils';

/**
 * ฟังก์ชันคำนวณ State เริ่มต้นของ Session และ Active Session ID
 * @returns {{ sessions: Array, activeSessionId: string }}
 */
function computeInitialSessionState() {
  const saved = localStorage.getItem('tuh_chats');
  let loadedSessions = null;
  if (saved) {
    try {
      loadedSessions = JSON.parse(saved);
    } catch (e) {
      console.error("Failed to parse saved chats:", e);
    }
  }

  const savedWelcome = localStorage.getItem('tuh_welcome_message') || DEFAULT_WELCOME_MESSAGE;

  // โครงสร้าง Session เริ่มต้น (Default Session)
  const defaultSession = {
    id: 'session-1',
    title: 'สอบถามข้อมูลเบื้องต้น',
    createdAt: Date.now(),
    messages: [
      {
        id: 'm1',
        sender: 'bot',
        text: savedWelcome,
        timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
      }
    ]
  };

  // ตรวจสอบเวลาการใช้งานล่าสุด (ถ้าไม่ได้ใช้งานเกิน 1 ชั่วโมง ให้เคลียร์ประวัติเก่า)
  const lastChatTime = localStorage.getItem('tuh_last_chat_time');
  const now = Date.now();
  const oneHourInMs = 60 * 60 * 1000; // 1 ชั่วโมง = 3,600,000 มิลลิวินาที

  if (lastChatTime) {
    const elapsed = now - parseInt(lastChatTime, 10);
    if (elapsed > oneHourInMs) {
      localStorage.removeItem('tuh_chats');
      localStorage.removeItem('tuh_last_chat_time');
      return { sessions: [defaultSession], activeSessionId: defaultSession.id };
    }
  }

  if (!loadedSessions || loadedSessions.length === 0) {
    return { sessions: [defaultSession], activeSessionId: defaultSession.id };
  }

  // กรองข้อมูลเซสชันที่ไม่หมดอายุ (<= 1 ชั่วโมง)
  const validSessions = loadedSessions.map(session => {
    if (!session.createdAt) {
      if (session.id && session.id.startsWith('session-')) {
        const timestampStr = session.id.substring(8);
        const parsedTimestamp = parseInt(timestampStr, 10);
        if (!isNaN(parsedTimestamp) && parsedTimestamp > 1000000000000) {
          session.createdAt = parsedTimestamp;
        } else {
          session.createdAt = now;
        }
      } else {
        session.createdAt = now;
      }
    }
    return session;
  }).filter((session, idx) => {
    if (idx === 0) return true; // เก็บห้องแรกไว้เสมอ
    return (now - session.createdAt) <= oneHourInMs;
  });

  if (validSessions.length === 0) {
    return { sessions: [defaultSession], activeSessionId: defaultSession.id };
  }

  // หากห้องล่าสุดมีการคุยข้อความแล้ว ให้เปิดห้องใหม่รอไว้
  const mostRecent = validSessions[0];
  if (mostRecent && mostRecent.messages.length > 1) {
    const newId = `session-${now}`;
    const newSession = {
      id: newId,
      title: `บทสนทนาใหม่ #${validSessions.length + 1}`,
      createdAt: now,
      messages: [
        {
          id: `m-${now}`,
          sender: 'bot',
          text: localStorage.getItem('tuh_chat_greeting') || DEFAULT_GREETING,
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        }
      ]
    };

    return { sessions: [newSession, ...validSessions], activeSessionId: newId };
  }

  return { sessions: validSessions, activeSessionId: mostRecent ? mostRecent.id : 'session-1' };
}

export function useChatSessions({ currentTime, setIsSidebarOpen }) {
  // ใช้ useRef เพื่อคำนวณ State เริ่มต้นเพียงครั้งเดียว ป้องกันปัญหา React StrictMode
  const initialStateRef = useRef(null);
  if (initialStateRef.current === null) {
    initialStateRef.current = computeInitialSessionState();
  }

  const [sessions, setSessions] = useState(initialStateRef.current.sessions);
  const [activeSessionId, setActiveSessionId] = useState(initialStateRef.current.activeSessionId);

  // ซิงค์ข้อมูล sessions ลง localStorage ทุกครั้งที่มีการเปลี่ยนแปลง
  useEffect(() => {
    localStorage.setItem('tuh_chats', JSON.stringify(sessions));
  }, [sessions]);

  // ตรวจสอบและลบเซสชันที่หมดอายุอัตโนมัติ (เกิน 1 ชั่วโมง)
  useEffect(() => {
    if (sessions.length <= 1) return;
    const now = Date.now();
    const oneHourInMs = 60 * 60 * 1000;

    const expiredSessionsExist = sessions.some((s, idx) => {
      if (idx === 0) return false;
      const elapsed = now - (s.createdAt || now);
      return elapsed > oneHourInMs;
    });

    if (expiredSessionsExist) {
      const filtered = sessions.filter((s, idx) => {
        if (idx === 0) return true;
        const elapsed = now - (s.createdAt || now);
        return elapsed <= oneHourInMs;
      });

      setSessions(filtered);

      // หาก session ปัจจุบันถูกลบ ให้สลับไปยัง session แรก
      if (!filtered.some(s => s.id === activeSessionId)) {
        setActiveSessionId(filtered[0].id);
      }
    }
  }, [currentTime, sessions, activeSessionId]);

  // คำนวณ Session ปัจจุบันที่กำลังแสดงผล
  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || { messages: [] };
  // ตรวจสอบว่า Session ปัจจุบันเป็น Session ล่าสุด (ห้องบนสุด) หรือไม่
  const isActiveSessionLatest = activeSessionId === sessions[0]?.id;

  /**
   * สร้างบทสนทนาใหม่ (New Chat Session)
   * @param {string} chatGreeting - ข้อความทักทายของบอท
   */
  const handleNewChat = (chatGreeting) => {
    const newId = `session-${Date.now()}`;
    const newSession = {
      id: newId,
      title: `บทสนทนาใหม่ #${sessions.length + 1}`,
      createdAt: Date.now(),
      messages: [
        {
          id: `m-${Date.now()}`,
          sender: 'bot',
          text: chatGreeting || DEFAULT_GREETING,
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        }
      ]
    };
    localStorage.setItem('tuh_last_chat_time', Date.now().toString());
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newId);
    setIsSidebarOpen(false);
  };

  /**
   * ลบบทสนทนาที่ระบุ ID
   * @param {string} id - Session ID ที่ต้องการลบ
   * @param {Event} e - Click event
   */
  const handleDeleteSession = (id, e) => {
    e.stopPropagation();
    // ป้องกันการลบห้องปัจจุบันที่กำลังใช้งานอยู่
    if (id === sessions[0]?.id) {
      alert("ไม่สามารถลบการสนทนาปัจจุบันที่กำลังใช้งานอยู่ได้ครับ");
      return;
    }
    // ป้องกันการลบจนไม่เหลือห้องสนทนา
    if (sessions.length === 1) {
      alert("ขาหมูขอชี้แจงว่าคุณผู้ใช้ไม่สามารถลบการสนทนาทั้งหมดได้ ต้องมีอย่างน้อย 1 รายการครับ");
      return;
    }
    const filtered = sessions.filter(s => s.id !== id);
    setSessions(filtered);
    if (activeSessionId === id) {
      setActiveSessionId(filtered[0].id);
    }
  };

  return {
    sessions, setSessions, activeSessionId, setActiveSessionId,
    activeSession, isActiveSessionLatest,
    handleNewChat, handleDeleteSession
  };
}

