import { useState, useRef, useEffect } from 'react';
import { DEFAULT_WELCOME_MESSAGE, DEFAULT_GREETING } from '../utils/chatUtils';

// คำนวณ sessions + activeSessionId เริ่มต้นแบบ pure function ในครั้งเดียว
// เดิมใช้ window.__initialActiveSessionId เป็นช่องทางลับส่งค่าจาก useState initializer ของ sessions
// ไปยัง useState initializer ของ activeSessionId ที่ประกาศถัดไปทันที (พึ่งพาลำดับการเรียก hook ของ React
// ตรงๆ และเสี่ยงพังภายใต้ React StrictMode ที่เรียก initializer function ซ้ำสองครั้งใน dev mode) —
// เปลี่ยนมาเป็นฟังก์ชันธรรมดาที่คืนค่าทั้งสองอย่างพร้อมกันในครั้งเดียว ไม่มี global state เลย
function computeInitialSessionState() {
  const saved = localStorage.getItem('tuh_chats');
  let loadedSessions = null;
  if (saved) {
    try {
      loadedSessions = JSON.parse(saved);
    } catch (e) {
      console.error(e);
    }
  }

  const savedWelcome = localStorage.getItem('tuh_welcome_message') || DEFAULT_WELCOME_MESSAGE;

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

  // ตรวจสอบการไม่ใช้งาน 1 ชั่วโมง
  const lastChatTime = localStorage.getItem('tuh_last_chat_time');
  const now = Date.now();
  const oneHourInMs = 60 * 60 * 1000;
  // ตั้งค่าเวลาสำหรับทดสอบการล็อกเอาต์อัตโนมัติภายใน 1 นาที
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

  // กรองข้อมูลแชทที่เก่าเกิน 1 ชั่วโมง (1 * 60 * 60 * 1000 = 3,600,000 ms)
  const validSessions = loadedSessions.map(session => {
    // ถ้า session ไม่มี createdAt ให้ลอง parse จาก ID, หรือใช้ค่าปัจจุบัน
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
    if (idx === 0) return true;
    return (now - session.createdAt) <= oneHourInMs;
  });

  if (validSessions.length === 0) {
    return { sessions: [defaultSession], activeSessionId: defaultSession.id };
  }

  // ตรวจสอบว่า session ล่าสุดมีข้อความหรือไม่
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

// สถานะการสนทนา: sessions, activeSessionId, effect เก็บ/หมดอายุอัตโนมัติ, activeSession/isActiveSessionLatest
// ที่คำนวณแบบ derived value, และ handler ที่เกี่ยวข้อง (handleNewChat, handleDeleteSession)
export function useChatSessions({ currentTime, setIsSidebarOpen }) {
  // ใช้ ref คุมให้ computeInitialSessionState() ทำงานแค่ครั้งเดียวต่อการ mount จริง (กันปัญหา React
  // StrictMode ที่เรียกฟังก์ชันซึ่งส่งเข้า useState ซ้ำสองครั้งใน dev mode) แล้วส่งค่าที่คำนวณเสร็จแล้ว
  // (เป็นค่าธรรมดา ไม่ใช่ฟังก์ชัน) เข้า useState ตรงๆ ทั้งสองตัว — จึงไม่มีปัญหาการ double-invoke เลย
  const initialStateRef = useRef(null);
  if (initialStateRef.current === null) {
    initialStateRef.current = computeInitialSessionState();
  }

  const [sessions, setSessions] = useState(initialStateRef.current.sessions);
  const [activeSessionId, setActiveSessionId] = useState(initialStateRef.current.activeSessionId);

  // บันทึกแชทลง localStorage
  useEffect(() => {
    localStorage.setItem('tuh_chats', JSON.stringify(sessions));
  }, [sessions]);

  // ตรวจสอบและลบเซสชันที่หมดอายุโดยอัตโนมัติเมื่อตัวนับถอยหลังถึง 00:00 (1 ชั่วโมง)
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

      if (!filtered.some(s => s.id === activeSessionId)) {
        setActiveSessionId(filtered[0].id);
      }
    }
  }, [currentTime, sessions, activeSessionId]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || { messages: [] };
  const isActiveSessionLatest = activeSessionId === sessions[0]?.id;

  // สร้างบทสนทนาใหม่ — รับ chatGreeting ปัจจุบันจากผู้เรียก เพราะค่านี้เป็นของ useWelcomeSettings
  // ซึ่งถูกเรียกทีหลัง hook นี้ใน App.jsx (useWelcomeSettings ต้องพึ่ง setSessions จาก hook นี้ก่อน)
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

  // ลบบทสนทนา
  const handleDeleteSession = (id, e) => {
    e.stopPropagation();
    if (id === sessions[0]?.id) {
      alert("ไม่สามารถลบการสนทนาปัจจุบันที่กำลังใช้งานอยู่ได้ครับ");
      return;
    }
    if (sessions.length === 1) {
      alert("ขาหมูขอชีแจงว่าคุณผู้ใช้ไม่สามารถลบการสนทนาทั้งหมดได้ ต้องมีอย่างน้อย 1 รายการครับ");
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
