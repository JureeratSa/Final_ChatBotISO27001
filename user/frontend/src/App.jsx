import React, { useState, useEffect, useRef } from 'react';
import logo from './logo.png';
import dog from './dog.png';
import dog_light from './dog_light.png';
import botAvatar from './bot_avatar.jpg';

const API_URL = `http://${window.location.hostname}:8000`;

const DEFAULT_WELCOME_MESSAGE = 'สวัสดีครับ TUH Chatbot AI  ยินดีให้บริการครับ \n\nมีข้อสงสัยเกี่ยวกับสวัสดีการสามารถสอบถามข้อมูลกับขาหมูได้เลยนะครับ';
const DEFAULT_GREETING = 'สวัสดีครับ! เริ่มต้นบทสนทนาใหม่แล้วครับ ท่านต้องการสอบถามข้อมูลส่วนใดของโรงพยาบาลธรรมศาสตร์ฯ หรือมีข้อขัดข้องเกี่ยวกับระบบสารสนเทศส่วนใด ถามเข้ามาได้เลยครับ 🏥🤖';

const stripHtml = (html) => {
  if (!html) return '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || "";
};

const formatAnnDate = (dateStr) => {
  if (!dateStr) return "";
  try {
    const cleanStr = dateStr.replace('T', ' ');
    const parts = cleanStr.split(' ');
    const dateParts = parts[0].split('-');
    if (dateParts.length !== 3) return dateStr;
    const year = parseInt(dateParts[0]);
    const month = parseInt(dateParts[1]);
    const day = parseInt(dateParts[2]);
    const time = parts[1] ? parts[1].substring(0, 5) : "";

    const monthNames = [
      "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
      "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
    ];

    const thaiYear = year + 543;
    const formattedDate = `${day} ${monthNames[month - 1]} ${thaiYear}`;
    return time ? `${formattedDate} เวลา ${time} น.` : formattedDate;
  } catch (e) {
    return dateStr;
  }
};



// สถานะเวลาปัจจุบันสำหรับการอัปเดตการนับถอยหลังแบบเรียลไทม์
function App() {
  const [currentTime, setCurrentTime] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // สถานะธีม
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_theme');
    if (saved !== null) {
      return saved === 'dark';
    }
    // ตั้งค่าเริ่มต้นเป็นโหมดสว่าง
    return false;
  });

  const currentMascot = isDarkMode ? dog : dog_light;
  const currentBotAvatar = isDarkMode ? botAvatar : dog_light;

  // สถานะความกว้างของแถบด้านข้าง
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('tuh_sidebar_width');
    return saved ? parseInt(saved, 10) : 320;
  });

  // สถานะขนาดฟอนต์
  const [fontSize, setFontSize] = useState(() => {
    const saved = localStorage.getItem('tuh_font_size');
    return saved || 'normal';
  });

  const isResizing = useRef(false);

  const startResizing = (e) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const startTouchResizing = (e) => {
    isResizing.current = true;
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing.current) return;
      let newWidth = e.clientX;
      const minWidth = 240;
      const maxWidth = Math.min(480, window.innerWidth * 0.85);
      if (newWidth < minWidth) newWidth = minWidth;
      if (newWidth > maxWidth) newWidth = maxWidth;
      setSidebarWidth(newWidth);
    };

    const handleTouchMove = (e) => {
      if (!isResizing.current) return;
      if (e.touches && e.touches[0]) {
        let newWidth = e.touches[0].clientX;
        const minWidth = 240;
        const maxWidth = Math.min(480, window.innerWidth * 0.85);
        if (newWidth < minWidth) newWidth = minWidth;
        if (newWidth > maxWidth) newWidth = maxWidth;
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      if (isResizing.current) {
        isResizing.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        localStorage.setItem('tuh_sidebar_width', sidebarWidth);
      }
    };

    const handleTouchEnd = () => {
      if (isResizing.current) {
        isResizing.current = false;
        document.body.style.userSelect = '';
        localStorage.setItem('tuh_sidebar_width', sidebarWidth);
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [sidebarWidth]);

  // ข้อความต้อนรับ
  const [welcomeMessage, setWelcomeMessage] = useState(() => {
    return localStorage.getItem('tuh_welcome_message') || DEFAULT_WELCOME_MESSAGE;
  });

  // IP ของผู้ใช้
  const [userIp, setUserIp] = useState('127.0.0.1');

  // คำทักทายในฝั่งแชท
  const [chatGreeting, setChatGreeting] = useState(() => {
    return localStorage.getItem('tuh_chat_greeting') || DEFAULT_GREETING;
  });

  // สถานะการสนทนา
  const [sessions, setSessions] = useState(() => {
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
        return [defaultSession];
      }
    }

    if (!loadedSessions || loadedSessions.length === 0) {
      return [defaultSession];
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
      return [defaultSession];
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

      // เก็บ ID ของเซสชันที่ใช้งานไว้ใน window เพื่อให้ useState สามารถรับค่าได้
      window.__initialActiveSessionId = newId;
      return [newSession, ...validSessions];
    }

    window.__initialActiveSessionId = mostRecent ? mostRecent.id : 'session-1';
    return validSessions;
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    if (window.__initialActiveSessionId) {
      const id = window.__initialActiveSessionId;
      delete window.__initialActiveSessionId;
      return id;
    }
    return 'session-1';
  });

  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 768);
  const [showFaqs, setShowFaqs] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [copiedId, setCopiedId] = useState(null);
  const [faqsList, setFaqsList] = useState([]);

  // สถานะของฟอร์มแสดงความคิดเห็น
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [isForcedFeedback, setIsForcedFeedback] = useState(false);

  // คำถาม & แสดงความคิดเห็นที่ไม่พอใจ
  const [questionCount, setQuestionCount] = useState(() => {
    const saved = sessionStorage.getItem('tuh_question_count');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [showDislikeModal, setShowDislikeModal] = useState(false);
  const [dislikeQuestion, setDislikeQuestion] = useState('');
  const [dislikeAnswer, setDislikeAnswer] = useState('');
  const [dislikeMsgId, setDislikeMsgId] = useState('');
  const [dislikeReason, setDislikeReason] = useState('');
  const [dislikeSuccess, setDislikeSuccess] = useState(false);

  const [activeAnnouncements, setActiveAnnouncements] = useState([]);
  const [showAnnModal, setShowAnnModal] = useState(false);

  const handleCloseAnnModal = () => {
    setShowAnnModal(false);
    sessionStorage.setItem('tuh_announcements_seen', 'true');
  };

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

  // ารประสานสถานะธีมเข้ากับคลาสในแท็ก HTML
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tuh_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tuh_theme', 'light');
    }
  }, [isDarkMode]);

  // ปรับปรุงขนาดฟอนต์บนระดับ HTML
  useEffect(() => {
    localStorage.setItem('tuh_font_size', fontSize);
    if (fontSize === 'large') {
      document.documentElement.style.fontSize = '19px';
    } else if (fontSize === 'xl') {
      document.documentElement.style.fontSize = '22px';
    } else {
      // 'normal'
      document.documentElement.style.fontSize = '16px';
    }
  }, [fontSize]);

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

    // โหลดประกาศที่กำลังเปิดใช้งานอยู่
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

    // โหลด IP เครื่องของผู้ใช้งาน
    fetch(API_URL + '/api/ip')
      .then(res => res.json())
      .then(data => {
        if (data && data.ip) {
          setUserIp(data.ip);
        }
      })
      .catch(err => console.error("Error fetching client IP:", err));
  }, []);

  // แสดงหรือซ่อนคำถามที่พบบ่อย (FAQs) โดยอัตโนมัติตามข้อความในแชทปัจจุบัน เมื่อ activeSessionId มีการเปลี่ยนแปลง
  useEffect(() => {
    const session = sessions.find(s => s.id === activeSessionId);
    if (session) {
      setShowFaqs(session.messages.length <= 1);
    }
  }, [activeSessionId]);

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

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || { messages: [] };
  const isActiveSessionLatest = activeSessionId === sessions[0]?.id;

  // สร้างบทสนทนาใหม่
  const handleNewChat = () => {
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

    // เรียก API ค้นหาแบบผสม (FAISS + BM25) ของ Python
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
        let botResponseText = data.answer || getBotResponse(text);
        botResponseText = botResponseText.replaceAll("__API_URL__", API_URL);

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
        if (nextCount === 3 && sessionStorage.getItem('tuh_feedback_submitted') !== 'true') {
          setTimeout(() => {
            setIsForcedFeedback(false);
            setShowFeedback(true);
          }, 1000);
        }
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
          return;
        }

        abortControllerRef.current = null;
        console.warn("API Search failed, using static fallback:", error);
        // ใช้ค่าเริ่มต้นแทนหากเกิดข้อผิดพลาด
        const botResponseText = getBotResponse(text);
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
        if (nextCount === 3 && sessionStorage.getItem('tuh_feedback_submitted') !== 'true') {
          setTimeout(() => {
            setIsForcedFeedback(false);
            setShowFeedback(true);
          }, 1000);
        }
      });
  };

  // ระบบกำหนดเส้นทางการตอบกลับของบอทแบบปรับแต่งเอง
  const getBotResponse = (text) => {
    const t = text.toLowerCase().trim();

    // ตรวจสอบว่าตรงกับคำถามที่พบบ่อย (FAQs) หรือไม่
    for (const faq of faqsList) {
      if (t === faq.question.toLowerCase().trim() || t.includes(faq.question.substring(0, 20).toLowerCase())) {
        if (faq.response && faq.response.trim() !== '') {
          return faq.response;
        }
      }
    }


    // ตรวจสอบคำสำคัญ
    if (t.includes('ดวงตา') || t.includes('จ้องจอ') || t.includes('ถนอมสายตา') || t.includes('ปวดตา') || t.includes('เมื่อยตา')) {
      return faqsList[0]?.response || '';
    }
    if (t.includes('ผู้ป่วยใหม่') || t.includes('ทำบัตร') || t.includes('บัตรผู้ป่วย') || t.includes('เวชระเบียน')) {
      return faqsList[1]?.response || '';
    }
    if (t.includes('ติดต่อไอที') || t.includes('สารสนเทศ') || t.includes('แผนกไอที') || t.includes('เบอร์ไอที') || t.includes('แจ้งปัญหา')) {
      return faqsList[2]?.response || '';
    }
    if (t.includes('นอกเวลา') || t.includes('คลินิกนอกเวลา') || t.includes('เวลาทำการ') || t.includes('เปิดกี่โมง')) {
      return faqsList[3]?.response || '';
    }
    if (t.includes('เช็คสิทธิ์') || t.includes('สิทธิการรักษา') || t.includes('บัตรทอง') || t.includes('ประกันสังคม') || t.includes('ข้าราชการ')) {
      return faqsList[4]?.response || '';
    }
    if (t.includes('tuh easy app') || t.includes('easy app') || t.includes('แอปโรงพยาบาล') || t.includes('จองคิวตรวจ') || t.includes('ดาวน์โหลดแอป')) {
      return faqsList[5]?.response || '';
    }
    if (t.includes('สวัสดี') || t.includes('ดีครับ') || t.includes('hello') || t.includes('hi')) {
      return "สวัสดีครับ! ยินดีต้อนรับสู่ **TUH Chatbot AI** ยินดีที่ได้พูดคุยกับท่านครับ 😊 มีข้อมูลบริการใดหรือเรื่องระบบไอทีที่คุณต้องการสอบถามงานสารสนเทศเพิ่มเติมไหมครับ?";
    }
    if (t.includes('ขอบคุณ') || t.includes('thank')) {
      return "ด้วยความยินดีอย่างยิ่งครับ! หากมีข้อสงสัยหรือข้อขัดข้องเรื่องใดเพิ่มเติม สามารถพิมพ์ถามผมได้ตลอดเวลาเลยนะครับ ขอให้มีสุขภาพดวงตาและสุขภาพกายที่แข็งแรงครับ 🏥💚";
    }

    // ค่าเริ่มต้นแทน
    return `ขอบคุณสำหรับคำถามครับคุณผู้ใช้ ผมเป็นระบบปัญญาประดิษฐ์ให้ข้อมูลเบื้องต้นของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ สำหรับคำถามเกี่ยวกับการรักษาเฉพาะทางลึกหรือข้อมูลอื่นๆ นอกเหนือจากนี้ ท่านสามารถติดต่อเพิ่มเติมได้ที่:\n\n` +
      `📞 **สายด่วนโรงพยาบาล (ประชาสัมพันธ์):** โทร. 02-926-9999\n` +
      `🏢 **งานสารสนเทศ (ไอที):** โทร. 02-926-9999 ต่อ 7120\n\n` +
      `ท่านสามารถส่งความคิดเห็นและข้อแนะนำการบริการผ่านเมนู **"ข้อเสนอแนะ"** ที่มุมซ้ายล่างได้เลยครับ เพื่อให้ทีมงานสารสนเทศนำไปปรับปรุงระบบแชทบอทให้ตอบคำถามได้หลากหลายและดียิ่งขึ้นครับ`;
  };

  // จัดการข้อความถูกใจ/ไม่ถูกใจของบอท
  const handleLikeMessage = (msgId, likedState) => {
    let msgText = '';
    let userQuery = '';

    // ค้นหาข้อความพร้อมกันในสถานะ sessions ปัจจุบัน
    const currentSession = sessions.find(s => s.id === activeSessionId);
    if (currentSession) {
      const msgIndex = currentSession.messages.findIndex(m => m.id === msgId);
      if (msgIndex !== -1) {
        msgText = currentSession.messages[msgIndex].text;
        if (msgIndex > 0) {
          userQuery = currentSession.messages[msgIndex - 1].text;
        }

        // ตรวจสอบว่าผู้ใช้กำลังไม่พอใจกับข้อความหรือไม่ (เปลี่ยนจากไม่พอใจเป็นไม่พอใจ)
        const isDisliking = likedState === 'dislike' && !currentSession.messages[msgIndex].disliked;
        if (isDisliking) {
          setDislikeQuestion(userQuery || 'ไม่พบคำถาม');
          setDislikeAnswer(msgText);
          setDislikeMsgId(msgId);
          setDislikeReason('');
          setDislikeSuccess(false);
          setShowDislikeModal(true);
        }
      }
    }

    setSessions(prevSessions => prevSessions.map(s => {
      if (s.id === activeSessionId) {
        return {
          ...s,
          messages: s.messages.map(m => {
            if (m.id === msgId) {
              const newLiked = likedState === 'like' ? !m.liked : false;
              const newDisliked = likedState === 'dislike' ? !m.disliked : false;

              // ส่งบันทึกการให้คะแนนไปยังส่วนหลังบ้าน
              fetch(API_URL + '/api/admin/feedback/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  msgId: msgId,
                  rating: newLiked ? 'like' : (newDisliked ? 'dislike' : ''),
                  comment: '',
                  query: userQuery || msgText.substring(0, 30),
                  answer: msgText
                })
              }).catch(err => console.error("Failed to submit feedback rating:", err));

              return {
                ...m,
                liked: newLiked,
                disliked: newDisliked
              };
            }
            return m;
          })
        };
      }
      return s;
    }));
  };

  // จัดการส่งคำอธิบายเพิ่มเติมสำหรับข้อความที่ไม่พอใจ
  const handleDislikeSubmit = (e) => {
    e.preventDefault();
    if (!dislikeReason.trim()) return;

    fetch(API_URL + '/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        msgId: dislikeMsgId,
        rating: 'dislike',
        comment: dislikeReason,
        query: dislikeQuestion,
        answer: dislikeAnswer
      })
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setDislikeSuccess(true);
          setTimeout(() => {
            setShowDislikeModal(false);
            setDislikeSuccess(false);
            setDislikeReason('');
          }, 1500);
        }
      })
      .catch(err => {
        console.error("Failed to submit dislike explanation:", err);
        // ส่วนสำรอง (Fallback): ให้แสดงผลสถานะว่าสำเร็จและปิด [ฟอร์ม/หน้าต่าง] ไป เพื่อไม่ให้ผู้ใช้งานติดขัดหรือค้างอยู่หน้าเดิม
        setDislikeSuccess(true);
        setTimeout(() => {
          setShowDislikeModal(false);
          setDislikeSuccess(false);
          setDislikeReason('');
        }, 1500);
      });
  };

  // คัดลอกข้อความ
  const handleCopyMessage = (text, msgId) => {
    // ลบรูปแบบตัวหนาและรูปแบบลิงก์ของ Markdown ออกเพื่อให้เป็นข้อความธรรมดาที่สะอาดตา โดยยังคงรักษาการขึ้นบรรทัดใหม่ไว้
    let cleanedText = text;
    cleanedText = cleanedText.replace(/\*\*(.*?)\*\*/g, '$1');
    cleanedText = cleanedText.replace(/\[(.*?)\]\((.*?)\)/g, '$1 ($2)');

    navigator.clipboard.writeText(cleanedText).then(() => {
      setCopiedId(msgId);
      setTimeout(() => {
        setCopiedId(null);
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
    });
  };

  // ปิดแชทบอท
  const handleCloseChatbot = () => {
    const feedbackSubmitted = sessionStorage.getItem('tuh_feedback_submitted');
    if (feedbackSubmitted === 'true') {
      window.location.href = "https://intranet.hospital.tu.ac.th/";
    } else {
      setIsForcedFeedback(true);
      setShowFeedback(true);
    }
  };

  // จัดการส่งข้อเสนอแนะ
  const handleFeedbackSubmit = (e) => {
    e.preventDefault();

    // สร้างบันทึกข้อเสนอแนะ
    const feedbackData = {
      rating: feedbackRating >= 4 ? 'like' : 'dislike',
      stars: feedbackRating,
      comment: feedbackText,
      query: isForcedFeedback ? 'บังคับกรอกก่อนปิดหน้าต่าง' : 'ความคิดเห็นทั่วไปจากแบบฟอร์ม',
      msgId: `feedback-${Date.now()}`
    };

    // ส่งไปยัง API ส่วนหลังบ้าน
    fetch(API_URL + '/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    })
      .then(r => r.json())
      .then(data => {
        sessionStorage.setItem('tuh_feedback_submitted', 'true');
        // บันทึกในเครื่องด้วย
        const savedFeedback = localStorage.getItem('tuh_feedback_logs') || '[]';
        try {
          const logs = JSON.parse(savedFeedback);
          logs.push({
            rating: feedbackRating,
            comment: feedbackText,
            timestamp: new Date().toLocaleString('th-TH')
          });
          localStorage.setItem('tuh_feedback_logs', JSON.stringify(logs));
        } catch (err) {
          console.error(err);
        }
        setFeedbackSuccess(true);
      })
      .catch(err => {
        sessionStorage.setItem('tuh_feedback_submitted', 'true');
        console.error("Failed to submit feedback comments:", err);
        setFeedbackSuccess(true);
      });

    setTimeout(() => {
      setShowFeedback(false);
      setFeedbackSuccess(false);
      setFeedbackRating(5);
      setFeedbackText('');
      if (isForcedFeedback) {
        window.location.href = "https://intranet.hospital.tu.ac.th/";
      }
    }, 2000);
  };

  // แปลงข้อความดิบเป็น HTML ด้วยการแยกวิเคราะห์ Markdown แบบง่าย
  const parseMarkdown = (text) => {
    if (!text) return '';
    // Bold parsing (**text**)
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-tuh-navy dark:text-white">$1</strong>');
    // Bullet list items (- item or * item)
    html = html.replace(/^[-\*]\s*(.*?)$/gm, '<li class="ml-4 list-disc">$1</li>');
    // Number list items (1. item)
    html = html.replace(/^\d+\.\s(.*?)$/gm, '<li class="ml-4 list-decimal">$1</li>');
    // Link parsing [text](url)
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-tuh-rose dark:text-tuh-coral hover:text-tuh-coral dark:hover:text-tuh-pink underline font-semibold hover:opacity-80 transition">$1 <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i></a>');
    // Replace newlines with <br/>
    html = html.replace(/\n/g, '<br/>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="h-screen w-screen p-4 md:p-6 lg:p-8 bg-zayg-gradient box-border overflow-hidden flex font-sans text-tuh-navy dark:text-white transition-colors duration-300">
      <div className="flex-1 flex h-full overflow-hidden bg-white/70 dark:bg-tuh-navy/70 backdrop-blur-md rounded-[24px] border border-slate-300 dark:border-white/20 shadow-2xl relative">

        {/* 1. LEFT SIDEBAR PANEL (หน้าต่างซ้าย)  */}
        {isSidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-20 md:hidden transition-opacity duration-300"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        <aside
          style={{
            '--sidebar-width': isSidebarOpen ? `${fontSize === 'xl' ? Math.max(385, sidebarWidth + 60) :
              fontSize === 'large' ? Math.max(355, sidebarWidth + 30) :
                sidebarWidth
              }px` : '0px'
          }}
          className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-slate-200 dark:border-tuh-purple/20 bg-white dark:bg-tuh-indigo/90 backdrop-blur-md shadow-sm transition-all duration-300 md:static md:relative tuh-resizable-sidebar ${isSidebarOpen ? 'translate-x-0 opacity-100' : '-translate-x-full md:translate-x-0 md:opacity-0 md:border-r-0 overflow-hidden'
            }`}
        >

          {/* หัวข้อแถบด้านข้าง */}
          <div className="p-4 border-b border-slate-100 dark:border-tuh-purple/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <a
                href="https://intranet.hospital.tu.ac.th/"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-sm overflow-hidden p-0.5 border border-slate-100 dark:border-tuh-purple/10 shrink-0 group/logo cursor-pointer hover:shadow-md transition-all active:scale-95"
                title="ไปยังหน้าอินทราเน็ตโรงพยาบาล"
              >
                <img src={logo} alt="TUH Logo" className="w-full h-full object-contain transition-transform duration-300 group-hover/logo:scale-110" />
              </a>
              <div>
                <h2 className="font-extrabold text-tuh-navy dark:text-white leading-none font-roboto" style={{ fontSize: '1.5rem' }}>TUH</h2>
                <span className="text-black dark:text-white font-bold block mt-0.5 font-roboto" style={{ fontSize: '0.9rem' }}>Thammasat University Hospital</span>
              </div>
            </div>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-1 rounded-lg text-tuh-indigo/40 hover:text-tuh-rose hover:bg-slate-100 dark:text-slate-400 dark:hover:text-tuh-pink dark:hover:bg-tuh-indigo/40 transition shrink-0 active:scale-95"
              title="ปิดแถบเมนู"
            >
              <i className="fa-solid fa-chevron-left text-xs"></i>
            </button>
          </div>

          {/* ปุ่มเริ่มบทสนทนาใหม่ */}
          <div className="p-4 flex justify-center">
            <button
              onClick={handleNewChat}
              className="max-w-[16rem] w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-full bg-tuh-purple text-white hover:bg-tuh-rose hover:scale-[1.04] transition-all duration-300 active:scale-[0.98] text-sm font-semibold group shadow-sm hover:shadow-lg hover:shadow-tuh-rose/35"
            >
              <i className="fa-solid fa-plus text-xs opacity-80 transition-transform duration-300 group-hover:rotate-90"></i>
              เริ่มบทสนทนาใหม่
            </button>
          </div>

          {/* ประวัติการสนทนา */}
          <div className="flex-1 overflow-y-auto px-3 py-2 custom-scrollbar">
            <div className="px-3 mb-2 flex items-baseline gap-1.5 select-none">
              <span className="text-sm font-bold text-tuh-indigo/50 dark:text-slate-300 uppercase tracking-wider">
                ประวัติการสนทนา
              </span>
              <span className="text-[0.6875rem] font-semibold text-tuh-rose/70">
                (หมดอายุใน 1 ชม.)
              </span>
            </div>
            <div className="space-y-1">
              {sessions.map(s => {
                const isActive = s.id === activeSessionId;

                // คำนวณเวลาที่เหลือสำหรับเซสชันนี้
                const elapsed = currentTime - (s.createdAt || currentTime);
                const remaining = (60 * 60 * 1000) - elapsed;
                const m = Math.max(0, Math.floor(remaining / 60000));
                const sec = Math.max(0, Math.floor((remaining % 60000) / 1000));
                const countdownText = `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;

                return (
                  <div
                    key={s.id}
                    onClick={() => {
                      setActiveSessionId(s.id);
                      setIsSidebarOpen(false);
                    }}
                    className={`w-full group flex items-center justify-between py-2 px-3 rounded-xl cursor-pointer transition-all duration-200 ${isActive
                      ? 'tuh-sidebar-active'
                      : 'tuh-sidebar-inactive'
                      }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden flex-1">
                      <i className={`fa-solid ${isActive ? 'fa-message text-tuh-rose dark:text-tuh-coral' : 'fa-comment text-tuh-indigo/40 dark:text-slate-400'} text-sm shrink-0`}></i>
                      <span className="text-sm truncate flex-1 min-w-0 pr-1">{s.title}</span>
                      {s.id !== sessions[0]?.id && (
                        <span className={`text-xs font-bold shrink-0 px-2 py-0.5 rounded-lg bg-slate-100/80 dark:bg-white/15 text-tuh-indigo/70 dark:text-slate-200 flex items-center gap-1 ${isActive ? 'text-tuh-rose dark:text-tuh-pink bg-tuh-rose/10 dark:bg-tuh-rose/20' : ''}`}>
                          <i className="fa-regular fa-clock text-[11px]"></i>
                          {countdownText}
                        </span>
                      )}
                    </div>
                    {s.id !== sessions[0]?.id && (
                      <button
                        onClick={(e) => handleDeleteSession(s.id, e)}
                        className="opacity-0 group-hover:opacity-100 hover:text-red-500 p-1 rounded-md text-tuh-indigo/40 dark:text-slate-400 hover:bg-tuh-indigo/20 transition-all shrink-0 ml-1.5"
                        title="ลบการสนทนานี้"
                      >
                        <i className="fa-solid fa-trash-can text-xs"></i>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ปุ่มเมนูส่วนล่าง */}
          <div className="p-4 border-t border-slate-100 dark:border-tuh-purple/20 space-y-2 bg-slate-50/50 dark:bg-tuh-navy/40">

            {/* สลับโหมดหน้าจอ */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
            >
              <div className="flex items-center gap-3">
                <i className={`fa-solid ${isDarkMode ? 'fa-sun text-amber-500' : 'fa-moon text-blue-500'} text-base transition-transform duration-300 group-hover:scale-120 group-hover:rotate-12`}></i>
                <span className="text-sm font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">ปรับโหมดหน้าจอ</span>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200/60 dark:bg-white/10 text-tuh-navy/60 dark:text-slate-200 font-semibold group-hover:bg-tuh-rose/10 group-hover:text-tuh-rose dark:group-hover:text-white transition-all">
                {isDarkMode ? 'โหมดสว่าง' : 'โหมดมืด'}
              </span>
            </button>

            {/* ปรับขนาดตัวอักษร */}
            <div className="w-full flex flex-col gap-2 p-3 rounded-xl hover:bg-slate-100/50 dark:hover:bg-tuh-indigo/20 text-tuh-navy dark:text-slate-100 transition-all duration-300">
              <div className="flex items-center gap-3 select-none">
                <i className="fa-solid fa-font text-tuh-purple dark:text-purple-300 text-base"></i>
                <span className="text-sm font-medium">ขนาดตัวอักษร</span>
              </div>
              <div className="flex items-center gap-1 bg-slate-200/55 dark:bg-white/5 p-0.5 rounded-lg w-full">
                <button
                  onClick={() => setFontSize('normal')}
                  className={`flex-1 text-center text-[0.65rem] px-2 py-1 rounded-md font-semibold transition ${fontSize === 'normal' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
                >
                  ปกติ
                </button>
                <button
                  onClick={() => setFontSize('large')}
                  className={`flex-1 text-center text-[0.65rem] px-2 py-1 rounded-md font-semibold transition ${fontSize === 'large' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
                >
                  ใหญ่
                </button>
                <button
                  onClick={() => setFontSize('xl')}
                  className={`flex-1 text-center text-[0.65rem] px-2 py-1 rounded-md font-semibold transition ${fontSize === 'xl' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
                >
                  ใหญ่สุด
                </button>
              </div>
            </div>

            {/* ปุ่มคู่มือการใช้งาน */}
            <button
              onClick={() => { setShowGuide(true); setIsSidebarOpen(false); }}
              className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
            >
              <i className="fa-solid fa-book-open text-tuh-purple dark:text-purple-300 text-base transition-transform duration-300 group-hover:scale-120 group-hover:-rotate-6"></i>
              <span className="text-sm font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">คู่มือการใช้งาน</span>
            </button>

            {/* ปุ่มข้อเสนอแนะ */}
            <button
              onClick={() => { setIsForcedFeedback(false); setShowFeedback(true); setIsSidebarOpen(false); }}
              className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
            >
              <i className="fa-solid fa-comment-dots text-tuh-purple dark:text-purple-300 text-base transition-transform duration-300 group-hover:scale-120 group-hover:translate-y-[-2px]"></i>
              <span className="text-sm font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">ข้อเสนอแนะ</span>
            </button>

          </div>

          {/* แถบปรับขนาด (ทั้งเมาส์และสัมผัส) */}
          {isSidebarOpen && (
            <div
              onMouseDown={startResizing}
              onTouchStart={startTouchResizing}
              className="absolute top-0 right-0 bottom-0 w-3 -mr-1.5 cursor-col-resize z-50 group"
              title="ลากเพื่อปรับขนาดเมนู"
            >
              <div className="w-1 h-full mx-auto bg-transparent group-hover:bg-tuh-rose/40 dark:group-hover:bg-tuh-purple/40 transition-colors duration-150" />
            </div>
          )}
        </aside>

        {/* 2. หน้าต่างขวา */}
        <main className={`flex-1 flex flex-col justify-center items-center ${isSidebarOpen ? 'p-4' : 'p-0'} bg-white/20 dark:bg-tuh-navy/10 relative overflow-hidden h-full`}>

          {/* องค์ประกอบการออกแบบพื้นหลังแบบไดนามิกจากจานสีภาพผู้ใช้ */}
          <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/10 dark:bg-tuh-purple/20 blur-[100px] pointer-events-none animate-float-slow"></div>
          <div className="absolute bottom-40 left-10 w-96 h-96 rounded-full bg-tuh-purple/10 dark:bg-tuh-purple/10 blur-[120px] pointer-events-none animate-float-slower"></div>

          {activeSession.messages.length <= 1 ? (
            /* ==================== STATE A: หน้าจอเริ่มต้น (เมื่อไม่มีการสนทนา) ==================== */
            <div className="w-full h-full flex flex-col relative overflow-hidden">
              {/* ส่วนหัว */}
              <div className="w-full p-5 md:p-7 flex flex-col lg:flex-row gap-3 lg:gap-0 items-start lg:items-center justify-between shrink-0 z-20">
                {/* ส่วนซ้าย: ปุ่มเมนูแฮมเบอร์เกอร์และเมนูแบบเลื่อนลง */}
                <div className="flex items-center gap-3">
                  {!isSidebarOpen && (
                    <button
                      onClick={() => setIsSidebarOpen(true)}
                      className="p-2.5 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-white/50 dark:hover:bg-tuh-indigo/50 transition active:scale-95 shrink-0 bg-white/30 backdrop-blur-sm border border-white/40 dark:border-white/5 shadow-sm animate-fade-in"
                      title="เปิดแถบเมนู"
                    >
                      <i className="fa-solid fa-bars text-lg"></i>
                    </button>
                  )}
                  <div className="flex items-center gap-1.5 px-5 py-2 rounded-2xl bg-white/55 dark:bg-tuh-indigo/40 backdrop-blur-md border border-slate-300 dark:border-white/25 shadow-sm">
                    <span className="font-black tracking-tight text-tuh-gradient font-roboto" style={{ fontSize: '0.8rem' }}>TUH Chatbot AI</span>
                  </div>
                </div>

                {/* ส่วนขวา: ปุ่มติดต่อ */}
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-tuh-indigo/80 dark:text-slate-200 bg-white/55 dark:bg-tuh-indigo/40 px-5 py-2 rounded-2xl border border-slate-300 dark:border-white/25 flex items-center gap-1.5 shadow-sm">
                    <i className="fa-solid fa-desktop text-tuh-indigo/60 dark:text-slate-400 text-xs md:text-sm"></i>
                    IP: <span className="text-tuh-purple dark:text-purple-300 ml-1">{userIp}</span>
                  </span>
                  <span className="font-extrabold text-tuh-indigo/80 dark:text-slate-200 bg-white/55 dark:bg-tuh-indigo/40 px-5 py-2 rounded-2xl border border-slate-300 dark:border-white/25 flex items-center gap-1.5 shadow-sm">
                    <i className="fa-solid fa-phone text-tuh-rose animate-pulse text-xs md:text-sm"></i>
                    ระบบมีปัญหาติดต่อ 8471 หรือ 8343
                  </span>
                </div>
              </div>

              {/* เนื้อหาตรงกลาง */}
              <div className="flex-1 w-full overflow-y-auto custom-scrollbar z-10 px-4 pb-8 flex flex-col select-none">
                <div className="flex flex-col items-center text-center max-w-2xl mx-auto animate-fade-in my-auto py-6">
                  <img
                    src={currentMascot}
                    className={`${isDarkMode ? "w-64 md:w-80" : "w-44 md:w-52"} h-auto object-contain animate-mascot-float mb-5`}
                    style={isDarkMode ? {
                      WebkitMaskImage: 'radial-gradient(ellipse at center, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%)',
                      maskImage: 'radial-gradient(ellipse at center, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%)'
                    } : {}}
                    alt="Mascot"
                  />
                  <div className="mb-8 max-w-xl text-center leading-relaxed">
                    {welcomeMessage.includes('\n') ? (
                      <>
                        <div className="text-lg md:text-xl font-bold text-tuh-navy dark:text-white mb-1">
                          {parseMarkdown(welcomeMessage.split('\n')[0].trim())}
                        </div>
                        <div className="font-medium text-tuh-indigo/80 dark:text-slate-200 font-semibold">
                          {parseMarkdown(welcomeMessage.split('\n').slice(1).join('\n').trim())}
                        </div>
                      </>
                    ) : (
                      <div className="font-medium text-tuh-indigo/80 dark:text-slate-200 font-semibold">
                        {parseMarkdown(welcomeMessage)}
                      </div>
                    )}
                  </div>

                  {/* ช่องรับข้อความส่วนกลางจำลอง */}
                  <div className="w-full max-w-xl flex items-center gap-2 p-1.5 pl-4 rounded-2xl bg-white/70 dark:bg-[#1B2062]/60 border border-white/60 dark:border-white/10 shadow-lg backdrop-blur-md mb-6 focus-within:ring-2 focus-within:ring-tuh-rose/50 transition">
                    <input
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && inputValue.trim()) {
                          handleSendMessage(inputValue);
                        }
                      }}
                      placeholder="พิมพ์ข้อความของคุณเพื่อเริ่มต้นแชท..."
                      className="flex-1 bg-transparent border-none outline-none text-tuh-navy dark:text-white placeholder-tuh-indigo/45 dark:placeholder-white/40 font-medium py-2 px-1"
                    />
                    <button
                      onClick={() => {
                        if (inputValue.trim()) {
                          handleSendMessage(inputValue);
                        }
                      }}
                      className="w-10 h-10 rounded-xl bg-tuh-gradient-2 text-white flex items-center justify-center hover:scale-[1.05] active:scale-[0.98] transition"
                    >
                      <i className="fa-solid fa-paper-plane text-xs"></i>
                    </button>
                  </div>

                  {/* ปุ่มคำถามที่พบบ่อย */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full max-w-2xl px-4">
                    {faqsList.slice(0, 4).map(faq => (
                      <button
                        key={faq.id}
                        onClick={() => {
                          handleSendMessage(faq.question);
                        }}
                        className="flex items-center gap-3 px-5 py-3 text-xs md:text-sm font-semibold rounded-2xl bg-white/60 dark:bg-[#1B2062]/40 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-rose/25 dark:hover:text-white border border-slate-200/50 dark:border-white/5 shadow-sm transition-all active:scale-[0.98] w-full text-left"
                      >
                        <i className={`fa-solid ${faq.icon} text-tuh-rose shrink-0`}></i>
                        <span className="leading-snug">{faq.question}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ==================== STATE B: หน้าต่างแชทแบบเต็มหน้าจอ (เมื่อมีการสนทนา) ==================== */
            <div className={`w-full ${isSidebarOpen ? 'max-w-8xl h-[88vh] max-h-[850px] border-2 border-slate-300 dark:border-white/30 shadow-2xl rounded-[24px]' : 'h-full border-none shadow-none rounded-none'} flex flex-col bg-white/85 dark:bg-[#1B2062]/85 backdrop-blur-md overflow-hidden z-10 transition-all duration-300 animate-slide-in`}>
              {/* ส่วนหัวของหน้าต่างแชท */}
              <header className="p-4 md:px-6 md:py-4 border-b border-slate-200 dark:border-tuh-purple/20 bg-white/50 dark:bg-[#1B2062]/50 flex flex-col lg:flex-row gap-3 lg:gap-0 items-start lg:items-center justify-between shrink-0">
                <div className="flex items-center gap-3 w-full lg:w-auto">
                  {!isSidebarOpen && (
                    <button
                      onClick={() => setIsSidebarOpen(true)}
                      className="p-2.5 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-tuh-indigo/50 transition active:scale-95 shrink-0 animate-fade-in"
                      title="เปิดแถบเมนู"
                    >
                      <i className="fa-solid fa-bars text-lg"></i>
                    </button>
                  )}
                  <div className="min-w-0 flex-1 lg:flex-initial">
                    <h1 className="text-lg md:text-xl font-extrabold tracking-tight text-tuh-navy dark:text-white flex items-center gap-2">
                      <span className="text-tuh-coral shrink-0"><i className="fa-solid fa-circle-nodes"></i></span>
                      <span className="text-tuh-gradient font-black truncate font-roboto">TUH Chatbot AI</span>
                    </h1>
                    <p className="text-xs md:text-sm text-tuh-indigo/70 dark:text-slate-300 mt-0.5 md:mt-1 font-semibold text-left truncate">
                      งานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
                    </p>
                  </div>
                </div>
                <div className="w-full lg:w-auto flex justify-start lg:justify-end shrink-0 pl-12 md:pl-0 lg:pl-0 gap-2">
                  <span className="font-extrabold text-tuh-indigo/80 dark:text-slate-200 bg-slate-100 dark:bg-tuh-indigo/40 px-5 py-2 rounded-2xl border border-slate-300 dark:border-white/25 flex items-center gap-1.5 shadow-sm">
                    <i className="fa-solid fa-desktop text-tuh-indigo/60 dark:text-slate-400 text-xs md:text-sm"></i>
                    IP: <span className="text-tuh-purple dark:text-purple-300 ml-1">{userIp}</span>
                  </span>
                  <span className="font-extrabold text-tuh-indigo/80 dark:text-slate-200 bg-slate-100 dark:bg-tuh-indigo/40 px-5 py-2 rounded-2xl border border-slate-300 dark:border-white/25 flex items-center gap-1.5 shadow-sm">
                    <i className="fa-solid fa-phone text-tuh-rose animate-pulse text-xs md:text-sm"></i>
                    ระบบมีปัญหาติดต่อ 8471 หรือ 8343
                  </span>
                </div>
              </header>

              {/* พื้นที่แสดงข้อความแชท */}
              <div
                ref={chatContainerRef}
                className="flex-1 overflow-y-auto px-4 py-4 space-y-4 custom-scrollbar z-10"
              >
                {activeSession.messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-4 my-auto space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-tuh-pink/20 dark:bg-tuh-indigo/60 flex items-center justify-center text-tuh-rose dark:text-tuh-pink text-xl shadow-sm">
                      <i className="fa-solid fa-comments"></i>
                    </div>
                    <h4 className="text-sm font-bold text-tuh-navy dark:text-white">เริ่มการสนทนาของคุณ</h4>
                    <p className="text-xs text-tuh-indigo/60 dark:text-tuh-pink/70">
                      พิมพ์คำถามเกี่ยวกับการรับบริการโรงพยาบาลและประสานงานไอทีได้ที่ช่องพิมพ์ด้านล่าง
                    </p>
                  </div>
                ) : (
                  activeSession.messages.map((msg, index) => {
                    const isBot = msg.sender === 'bot';
                    return (
                      <div
                        key={msg.id || index}
                        className={`flex gap-2 max-w-[60%] ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'} animate-slide-in`}
                      >
                        {/* ไอคอนอวาตาร์ */}
                        {isBot ? (
                          <img
                            src={currentBotAvatar}
                            alt="Bot Icon"
                            className={`w-7 h-7 rounded-lg object-cover shrink-0 ${!isDarkMode ? 'object-top' : ''}`}
                          />
                        ) : (
                          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] shrink-0 shadow-sm text-white bg-tuh-gradient-1">
                            <i className="fa-solid fa-user"></i>
                          </div>
                        )}

                        {/* ฟองคำพูด */}
                        <div className="space-y-1 min-w-0">
                          <div className={`text-base leading-relaxed break-words ${isBot
                            ? 'p-3 rounded-2xl shadow-sm bg-slate-100 dark:bg-[#07010f] border border-slate-200/60 dark:border-tuh-purple/20 text-tuh-navy dark:text-white rounded-tl-sm'
                            : 'p-3 rounded-2xl shadow-md bg-[#f8bbd0] text-black dark:bg-[#ad1457] dark:text-white rounded-tr-sm'
                            }`}>
                            {parseMarkdown(msg.text)}
                          </div>

                          {isBot ? (
                            <div className="flex items-center gap-1.5 mt-1 px-0.5">
                              <button
                                onClick={() => handleLikeMessage(msg.id, 'like')}
                                className={`p-1 rounded-md text-[13px] transition-all ${msg.liked ? 'text-emerald-500 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-500 dark:hover:text-emerald-400'}`}
                              >
                                <i className={`fa-thumbs-up ${msg.liked ? 'fa-solid' : 'fa-regular'}`}></i>
                              </button>
                              <button
                                onClick={() => handleLikeMessage(msg.id, 'dislike')}
                                className={`p-1 rounded-md text-[13px] transition-all ${msg.disliked ? 'text-red-500 bg-red-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-red-500 dark:hover:text-red-400'}`}
                              >
                                <i className={`fa-thumbs-down ${msg.disliked ? 'fa-solid' : 'fa-regular'}`}></i>
                              </button>
                              <button
                                onClick={() => handleCopyMessage(msg.text, msg.id)}
                                className={`p-1 rounded-md text-[13px] transition-all flex items-center gap-0.5 ${copiedId === msg.id ? 'text-emerald-600 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-600 dark:hover:text-emerald-400'}`}
                              >
                                <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`}></i>
                              </button>
                              <span className="text-[12px] text-tuh-indigo/25 dark:text-slate-400/30">•</span>
                              <span className="text-[13px] text-tuh-indigo/40 dark:text-tuh-pink/40 font-medium">{msg.timestamp}</span>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end gap-1.5 mt-1 px-0.5">
                              <span className="text-[13px] text-tuh-indigo/40 dark:text-tuh-pink/40 font-medium">{msg.timestamp}</span>
                              <span className="text-[12px] text-tuh-indigo/25 dark:text-slate-400/30">•</span>
                              <button
                                onClick={() => {
                                  setInputValue(msg.text);
                                  const textarea = document.querySelector('.floating-textarea');
                                  if (textarea) textarea.focus();
                                }}
                                disabled={isTyping}
                                className="p-0.5 rounded-md text-[13px] text-tuh-indigo/35 dark:text-slate-400/50 hover:text-orange-500 dark:hover:text-orange-400"
                              >
                                <i className="fa-solid fa-arrow-rotate-left text-[12px]"></i>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}

                {isTyping && (
                  <div className="flex gap-2 max-w-[90%] mr-auto animate-slide-in">
                    <img
                      src={currentBotAvatar}
                      alt="Bot Icon"
                      className={`w-7 h-7 rounded-lg object-cover shrink-0 ${!isDarkMode ? 'object-top' : ''}`}
                    />
                    <div className="bg-slate-100 dark:bg-[#07010f] border border-slate-200/60 dark:border-tuh-purple/20 p-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2 h-2 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2 h-2 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* ส่วนรับข้อความ */}
              <div className="p-3 border-t border-slate-200/60 dark:border-tuh-purple/15 bg-white/50 dark:bg-[#1B2062]/50 shrink-0">
                {isActiveSessionLatest ? (
                  <div className="flex flex-col w-full">
                    {/* ปุ่มเปิดปิดคำถามที่พบบ่อย (FAQs) */}
                    <div className="flex items-center mb-2">
                      <button
                        onClick={() => setShowFaqs(!showFaqs)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-[#07010f] border border-slate-200 dark:border-tuh-purple/20 text-tuh-indigo/70 dark:text-slate-300 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-indigo/60 transition active:scale-95 shadow-sm"
                      >
                        <i className="fa-solid fa-circle-question text-tuh-rose dark:text-tuh-pink"></i>
                        <span>คำถามที่พบบ่อย (FAQs)</span>
                        <i className={`fa-solid ${showFaqs ? 'fa-chevron-down' : 'fa-chevron-up'} text-[10px] ml-1`}></i>
                      </button>
                    </div>

                    {/* รายการคำถามที่พบบ่อย (FAQs List) */}
                    {showFaqs && faqsList.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3 max-h-40 overflow-y-auto custom-scrollbar p-1.5 bg-slate-50/50 dark:bg-[#07010f]/30 rounded-xl border border-slate-200/40 dark:border-white/5 animate-slide-in">
                        {faqsList.map(faq => (
                          <button
                            key={faq.id}
                            onClick={() => handleSendMessage(faq.question)}
                            className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-[#1B2062]/55 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-rose/25 dark:hover:text-white border border-slate-200/60 dark:border-white/5 shadow-sm transition active:scale-[0.97] w-full text-left"
                          >
                            <i className={`fa-solid ${faq.icon || 'fa-lightbulb'} text-tuh-rose text-[11px] shrink-0`}></i>
                            <span className="leading-snug">{faq.question}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="flex items-end gap-2.5 w-full">
                      <textarea
                        ref={inputRef}
                        value={inputValue}
                        disabled={isTyping}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSendMessage(inputValue);
                          }
                        }}
                        rows={1}
                        placeholder={isTyping ? "กำลังประมวลผล..." : "พิมพ์ข้อความของคุณที่นี่..."}
                        className="floating-textarea flex-1 py-3 px-4 rounded-xl bg-slate-50 dark:bg-[#07010f] border border-slate-250 dark:border-tuh-purple/25 text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-white/40 focus:outline-none text-xs md:text-sm resize-none overflow-y-auto leading-normal focus:ring-2 focus:ring-tuh-rose/30 dark:focus:ring-tuh-rose/50 transition-all duration-300"
                      />

                      {isTyping ? (
                        <button
                          onClick={handleStopGeneration}
                          className="h-[46px] w-[46px] rounded-xl bg-gradient-to-r from-red-500 to-rose-600 text-white flex items-center justify-center hover:scale-[1.05] active:scale-[0.98] transition-all shrink-0 shadow-md hover:shadow-red-500/20"
                          title="หยุดหาคำตอบ"
                        >
                          <i className="fa-solid fa-stop text-sm"></i>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleSendMessage(inputValue)}
                          disabled={isTyping}
                          className="h-[46px] w-[46px] rounded-xl bg-tuh-gradient-2 text-white flex items-center justify-center hover:scale-[1.05] active:scale-[0.98] transition-all shrink-0 shadow-md hover:shadow-tuh-rose/20"
                          title="ส่งข้อความ"
                        >
                          <i className="fa-solid fa-paper-plane text-sm"></i>
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="w-full flex items-center justify-center p-3 rounded-xl bg-slate-100/80 dark:bg-tuh-navy/40 border border-slate-200 dark:border-white/5 text-slate-500 dark:text-slate-400 font-bold text-center text-xs md:text-sm select-none gap-2">
                    <i className="fa-solid fa-lock text-tuh-rose text-sm"></i>
                    <span>บทสนทนานี้หมดเวลาส่งข้อความแล้ว สามารถดูประวัติการสนทนาได้อย่างเดียว</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        {/*คู่มือการใช้งาน*/}
        {showGuide && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full max-h-[85vh] flex flex-col border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
              {/* ส่วนหัวของคู่มือการใช้งาน */}
              <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
                <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                  <i className="fa-solid fa-circle-info text-tuh-rose"></i>
                  คู่มือการใช้งานระบบแชทบอท
                </h3>
                <button
                  onClick={() => setShowGuide(false)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
                >
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>

              {/* เนื้อหาคู่มือการใช้งาน */}
              <div className="p-6 overflow-y-auto space-y-4 text-sm leading-relaxed custom-scrollbar text-tuh-navy/80 dark:text-tuh-pink/80">
                <p className="font-medium text-tuh-navy dark:text-white">
                  ระบบ TUH Chatbot AI พัฒนาขึ้นโดยงานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ เพื่อช่วยเหลือและตอบคำถามเบื้องต้นแก่ผู้ใช้บริการและบุคลากร
                </p>

                <div className="space-y-3">
                  <h4 className="font-bold text-tuh-navy dark:text-white border-l-4 border-tuh-rose pl-2">ความสามารถของระบบ:</h4>
                  <ul className="list-disc pl-5 space-y-1">
                    <li>สอบถามขั้นตอนรับบริการ เช่น การทำบัตรผู้ป่วยใหม่</li>
                    <li>ขอช่องทางติดต่อประสานงาน ฝ่ายสารสนเทศไอที</li>
                    <li>สอบถามเวลาทำการ ของคลินิกพิเศษนอกราชการ</li>
                    <li>ลิงก์การดาวน์โหลดและแนะนำการใช้งาน TUH Easy App</li>
                    <li>คำแนะนำการประเมินและดูแลรักษาสุขภาพดวงตากฎ 20-20-20</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="font-bold text-tuh-navy dark:text-white border-l-4 border-tuh-rose pl-2">วิธีใช้งานเบื้องต้น:</h4>
                  <ul className="list-decimal pl-5 space-y-1">
                    <li>กดเลือกที่แถบ **"คำถามที่พบบ่อย"** เพื่อรับคำตอบในเรื่องนั้นได้ทันที</li>
                    <li>พิมพ์ข้อความคำถามเกี่ยวกับสิทธิ์การรักษาพยาบาลหรือเรื่องระบบไอทีลงในช่องแชทเพื่อสอบถามระบบ</li>
                    <li>เปิดและสลับสิทธิ์หน้าต่างการแชท รวมถึงสร้าง **"เริ่มบทสนทนาใหม่"** ได้จากแถบด้านซ้าย</li>
                    <li>สามารถกดปิด/เปิดโหมดถนอมสายตาสำหรับหน้าจอที่เข้มขึ้นลดการล้าดวงตาได้ตลอดเวลา</li>
                  </ul>
                </div>

                <div className="p-3 bg-tuh-pink/10 dark:bg-tuh-purple/10 rounded-2xl border border-tuh-rose/20 dark:border-tuh-rose/30 flex gap-3 text-xs">
                  <i className="fa-solid fa-lightbulb text-amber-500 text-lg shrink-0"></i>
                  <p>
                    **ข้อแนะนำการดูแลดวงตา:** หากดวงตาต้องสัมผัสแสงหน้าจอเป็นเวลานาน แนะนำให้สลับเปิด **โหมดมืด (Dark Mode)** เพื่อให้โทนสีพื้นหลังลดการกระเจิงแสงสีฟ้า ช่วยลดความเหนื่อยล้าของสายตา
                  </p>
                </div>
              </div>

              {/* ปุ่มปิดคู่มือการใช้งาน */}
              <div className="p-4 bg-slate-50 dark:bg-tuh-navy/20 border-t border-slate-100 dark:border-tuh-purple/25 flex justify-end">
                <button
                  onClick={() => setShowGuide(false)}
                  className="px-5 py-2.5 rounded-xl bg-tuh-gradient-2 hover:opacity-90 text-white font-semibold text-sm transition"
                >
                  รับทราบและปิดหน้านี้
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 4. MODAL: ข้อเสนอแนะ */}
        {showFeedback && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
              {/* ส่วนหัวข้อเสนอแนะ */}
              <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
                <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                  <i className="fa-solid fa-comments text-tuh-rose"></i>
                  ส่งข้อเสนอแนะการใช้งาน
                </h3>
                {!isForcedFeedback && (
                  <button
                    onClick={() => setShowFeedback(false)}
                    className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
                  >
                    <i className="fa-solid fa-xmark"></i>
                  </button>
                )}
              </div>

              {/* เนื้อหาข้อเสนอแนะ */}
              {feedbackSuccess ? (
                <div className="p-8 text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-500 text-3xl flex items-center justify-center mx-auto animate-bounce">
                    <i className="fa-solid fa-circle-check"></i>
                  </div>
                  <h4 className="text-lg font-bold text-tuh-navy dark:text-white">ส่งข้อเสนอแนะเรียบร้อย!</h4>
                  <p className="text-sm text-tuh-indigo/60 dark:text-tuh-pink/60">
                    ขอบคุณสำหรับคำติชมและข้อแนะนำ งานสารสนเทศโรงพยาบาลธรรมศาสตร์ฯ จะนำไปพัฒนาแชทบอทให้ดียิ่งขึ้นครับ
                  </p>
                </div>
              ) : (
                <form onSubmit={handleFeedbackSubmit} className="p-6 space-y-4">

                  {/* แถบดาวแสดงความพึงพอใจ */}
                  <div>
                    <label className="block text-xs font-semibold text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คะแนนความพึงพอใจการใช้ระบบ</label>
                    <div className="flex gap-2 items-center">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          type="button"
                          key={star}
                          onClick={() => setFeedbackRating(star)}
                          className="text-2xl transition hover:scale-110 focus:outline-none"
                        >
                          <i className={`fa-solid fa-star ${star <= feedbackRating ? 'text-amber-400' : 'text-slate-200 dark:text-white'}`}></i>
                        </button>
                      ))}
                      <span className="text-xs text-tuh-indigo/40 dark:text-tuh-pink/40 font-bold ml-2">
                        ({feedbackRating} คะแนน)
                      </span>
                    </div>
                  </div>

                  {/* ช่องกรอกข้อความ */}
                  <div>
                    <label className="block text-xs font-semibold text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">ข้อแนะนำ / สิ่งที่ควรปรับปรุง</label>
                    <textarea
                      rows="3"
                      value={feedbackText}
                      onChange={(e) => setFeedbackText(e.target.value)}
                      placeholder="กรอกข้อความแนะนำระบบหรือแจ้งปัญหาไอทีที่พบเพิ่มเติมได้ที่นี่... (ไม่บังคับระบุ)"
                      className="w-full p-3 rounded-xl bg-slate-50 dark:bg-tuh-navy/55 border border-slate-200 dark:border-tuh-purple/30 text-sm focus:outline-none focus:ring-2 focus:ring-tuh-rose text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-tuh-pink/40 resize-none"
                    ></textarea>
                  </div>

                  {/* ปุ่มส่งข้อเสนอแนะและยกเลิก */}
                  <div className="flex justify-end gap-2 pt-2">
                    {!isForcedFeedback && (
                      <button
                        type="button"
                        onClick={() => setShowFeedback(false)}
                        className="px-4 py-2.5 rounded-xl border border-slate-250 dark:border-tuh-purple/40 text-tuh-indigo/70 dark:text-tuh-pink/70 hover:bg-slate-100 dark:hover:bg-tuh-indigo/60 font-semibold text-sm transition"
                      >
                        ยกเลิก
                      </button>
                    )}
                    <button
                      type="submit"
                      className="px-5 py-2.5 rounded-xl bg-tuh-gradient-2 hover:opacity-90 text-white font-semibold text-sm transition shadow-md shadow-tuh-rose/15"
                    >
                      {isForcedFeedback ? 'ส่งความเห็นเพื่อปิดแชทบอท' : 'ส่งข้อเสนอแนะ'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* 5. MODAL: DISLIKE FEEDBACK (ระบุเหตุผลที่ไม่ถูกใจ) */}
        {showDislikeModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
              {/* ส่วนหัวข้อเสนอแนะที่ไม่พึงพอใจ */}
              <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
                <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                  <i className="fa-solid fa-face-frown text-red-500"></i>
                  ระบุเหตุผลที่ไม่พึงพอใจ
                </h3>
                <button
                  onClick={() => setShowDislikeModal(false)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
                >
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>

              {/* เนื้อหาข้อเสนอแนะที่ไม่พึงพอใจ */}
              {dislikeSuccess ? (
                <div className="p-8 text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-500 text-3xl flex items-center justify-center mx-auto animate-bounce">
                    <i className="fa-solid fa-circle-check"></i>
                  </div>
                  <h4 className="text-lg font-bold text-tuh-navy dark:text-white">ขอบคุณสำหรับข้อมูล!</h4>
                  <p className="text-sm text-tuh-indigo/60 dark:text-tuh-pink/60">
                    เราจะนำข้อมูลนี้ไปปรับปรุงความถูกต้องของคำตอบให้ดียิ่งขึ้นครับ
                  </p>
                </div>
              ) : (
                <form onSubmit={handleDislikeSubmit} className="p-6 space-y-4">
                  {/* คำถาม (ปิด) */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คำถามของคุณ</label>
                    <div className="p-3.5 bg-slate-50 dark:bg-tuh-navy/30 border border-slate-200 dark:border-tuh-purple/10 rounded-2xl text-sm font-semibold text-slate-700 dark:text-slate-200 select-none max-h-24 overflow-y-auto">
                      {dislikeQuestion}
                    </div>
                  </div>

                  {/* คำตอบ (ปิด) */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คำตอบจากบอท</label>
                    <div className="p-3.5 bg-slate-50 dark:bg-tuh-navy/30 border border-slate-200 dark:border-tuh-purple/10 rounded-2xl text-sm text-slate-500 dark:text-slate-400 select-none max-h-36 overflow-y-auto whitespace-pre-wrap">
                      {dislikeAnswer}
                    </div>
                  </div>

                  {/* ช่องกรอกเหตุผลหรือข้อแก้ไขที่ถูกต้อง */}
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">ระบุเหตุผลหรือข้อแก้ไขที่ถูกต้อง <span className="text-red-500">*</span></label>
                    <textarea
                      rows="3"
                      required
                      value={dislikeReason}
                      onChange={(e) => setDislikeReason(e.target.value)}
                      placeholder="เช่น ข้อมูลคลาดเคลื่อน, ต้องการรายละเอียดเพิ่ม, คำตอบไม่ชัดเจน..."
                      className="w-full p-3.5 rounded-2xl bg-slate-50 dark:bg-tuh-navy/55 border border-slate-200 dark:border-tuh-purple/30 text-sm focus:outline-none focus:ring-2 focus:ring-tuh-rose text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-tuh-pink/40 resize-none font-medium"
                    ></textarea>
                  </div>

                  {/* ปุ่มส่งข้อเสนอแนะที่ไม่พึงพอใจและยกเลิก */}
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowDislikeModal(false)}
                      className="px-4 py-2.5 rounded-xl border border-slate-250 dark:border-tuh-purple/40 text-tuh-indigo/70 dark:text-tuh-pink/70 hover:bg-slate-100 dark:hover:bg-tuh-indigo/60 font-semibold text-sm transition"
                    >
                      ยกเลิก
                    </button>
                    <button
                      type="submit"
                      className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-500 to-rose-600 hover:opacity-90 text-white font-semibold text-sm transition shadow-md shadow-red-500/15"
                    >
                      ส่งคำอธิบาย
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* 6. MODAL: SYSTEM ANNOUNCEMENTS */}
        {showAnnModal && activeAnnouncements.length > 0 && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-xl w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden animate-scale-up">
              {/* Header */}
              <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex flex-col justify-start items-start gap-1 bg-slate-50 dark:bg-tuh-navy/35">
                <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                  <i className="fa-solid fa-bullhorn text-tuh-rose animate-bounce"></i>
                  ประกาศข่าวสารสำคัญ ({activeAnnouncements.length})
                </h3>
                <span className="text-xs font-semibold text-tuh-indigo/60 dark:text-tuh-pink/60 pl-7">
                  ประกาศจาก admin น้องขาหมู
                </span>
              </div>

              {/* Announcements List Container */}
              <div className="p-6 max-h-[60vh] overflow-y-auto space-y-4 custom-scrollbar">
                {activeAnnouncements.map((ann) => (
                  <div
                    key={ann.id}
                    className="p-5 rounded-2xl border border-slate-100 dark:border-tuh-purple/20 bg-slate-50/70 dark:bg-[#100220]/40 space-y-2.5 shadow-sm relative overflow-hidden text-left"
                  >
                    {/* Decorative color strip on left side */}
                    <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-tuh-rose to-tuh-pink"></div>

                    <div className="pl-2">
                      <h4 className="font-extrabold text-base text-tuh-navy dark:text-white flex items-center gap-2">
                        {ann.title}
                      </h4>
                      <p className="text-sm font-semibold text-slate-750 dark:text-slate-250 leading-relaxed mt-1 whitespace-pre-line mb-3">
                        {stripHtml(ann.content)}
                      </p>

                      {/* Date display at the bottom-left */}
                      {ann.start_date && (
                        <div className="text-[11px] font-medium text-slate-400 dark:text-tuh-pink/40 flex items-center gap-1.5 mt-2 pt-2 border-t border-slate-100 dark:border-tuh-purple/10">
                          <i className="fa-regular fa-clock text-tuh-rose/80 dark:text-tuh-pink/70"></i>
                          <span>เริ่มประกาศ: {formatAnnDate(ann.start_date)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="p-4 bg-slate-50 dark:bg-tuh-navy/35 border-t border-slate-100 dark:border-tuh-purple/25 flex justify-end">
                <button
                  onClick={handleCloseAnnModal}
                  className="px-6 py-2.5 rounded-xl bg-tuh-gradient-2 text-white font-bold text-sm transition hover:shadow-lg active:scale-[0.98] shadow-md shadow-tuh-rose/15"
                >
                  รับทราบ
                </button>
              </div>
            </div>
          </div>
        )}

      </div> {/* ปิดกล่องบรรจุแอปพลิเคชัน */}
    </div>
  );
}

export default App;
