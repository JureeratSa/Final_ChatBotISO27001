import React, { useState, useEffect, useRef } from 'react';
import logo from './logo.png';
import dog from './dog.png';
import dog_light from './dog_light.png';
import botAvatar from './bot_avatar.jpg';
import { Sidebar } from './components/Sidebar';
import { MessageBubble } from './components/MessageBubble';
import { InputBar } from './components/InputBar';
import { GuideModal } from './components/GuideModal';
import { FeedbackModal } from './components/FeedbackModal';
import { DislikeModal } from './components/DislikeModal';
import { AnnouncementModal } from './components/AnnouncementModal';

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
      return faqsList[0]?.response || "การดูแลรักษาดวงตาเมื่อต้องจ้องหน้าจอคอมพิวเตอร์เป็นเวลานาน สามารถทำได้โดยปฏิบัติตาม **กฎ 20-20-20** ดังนี้ครับ:\n\n1. **ทุกๆ 20 นาที:** ให้ละสายตาออกจากหน้าจอคอมพิวเตอร์\n2. **มองไปที่ระยะไกล 20 ฟุต:** เพื่อช่วยให้กล้ามเนื้อตาได้ผ่อนคลาย\n3. **กะพริบตาหรือมองค้างไว้ 20 วินาที:** ช่วยเพิ่มความชุ่มชื้นให้ดวงตา ลดอาการตาแห้งและอ่อนล้า\n\n🏥 **ข้อแนะนำเพิ่มเติม:**\n- ปรับความสว่างของหน้าจอและห้องทำงานให้เหมาะสม ไม่มืดหรือสว่างเกินไป\n- เปิดใช้งาน **โหมดมืด (Dark Mode)** ในระบบแชทบอท (แถบเมนูด้านซ้ายล่าง) เพื่อลดแสงสะท้อนและลดความเหนื่อยล้าของดวงตาครับ 😊";
    }
    if (t.includes('ผู้ป่วยใหม่') || t.includes('ทำบัตร') || t.includes('บัตรผู้ป่วย') || t.includes('เวชระเบียน')) {
      return faqsList[1]?.response || "สำหรับการลงทะเบียนทำบัตรประจำตัวผู้ป่วยใหม่ของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ สามารถดำเนินงานได้ดังนี้ครับ:\n\n📝 **เอกสารที่ต้องใช้:**\n- บัตรประจำตัวประชาชนตัวจริง (หรือสูติบัตรกรณีเป็นเด็ก)\n- บัตรรับรองสิทธิ์การรักษาพยาบาล (ถ้ามี เช่น สิทธิ์ส่งตัว, สิทธิ์ประกันสังคม)\n\n📍 **สถานที่ติดต่อ:**\n- สามารถยื่นเอกสารติดต่อได้ที่ **แผนกเวชระเบียน ชั้น 1 อาคารผู้ป่วยนอก (OPD)** โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ\n- หรือสามารถลงทะเบียนล่วงหน้าผ่านทางแอปพลิเคชัน **TUH Easy App** เพื่อความสะดวกรวดเร็วและลดเวลาในการรอคอยคิวครับ";
    }
    if (t.includes('ติดต่อไอที') || t.includes('สารสนเทศ') || t.includes('แผนกไอที') || t.includes('เบอร์ไอที') || t.includes('แจ้งปัญหา')) {
      return faqsList[2]?.response || "หากพี่ๆ เจ้าหน้าที่พบบัญหาขัดข้องเกี่ยวกับระบบสารสนเทศ คอมพิวเตอร์ หรือเครือข่ายอินเทอร์เน็ต สามารถติดต่อฝ่ายไอทีได้ที่ช่องทางต่อไปนี้ครับ:\n\n📞 **ช่องทางติดต่อภายใน (แผนกไอที):**\n- โทร. **8471** หรือ **8343** (ติดต่อแจ้งปัญหาการใช้งานทั่วไป)\n- ติดต่อห้องทำงานระบบเครือข่ายและระบบบริการสารสนเทศ: โทร. **7120**\n\n📧 **อีเมลหน่วยงาน:**\n- it@hospital.tu.ac.th\n\n*ช่วงเวลาทำการปกติ: วันจันทร์ - วันศุกร์ เวลา 08:00 น. - 16:00 น. (สำหรับปัญหาระบบล่มวิกฤตสามารถแจ้งเจ้าหน้าที่เวรนอกเวลาได้ครับ)*";
    }
    if (t.includes('นอกเวลา') || t.includes('คลินิกนอกเวลา') || t.includes('เวลาทำการ') || t.includes('เปิดกี่โมง')) {
      return faqsList[3]?.response || "**คลินิกพิเศษนอกเวลาราชการ** โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ เปิดให้บริการแก่ผู้รับบริการที่ต้องการความสะดวกนอกเวลาทำงานปกติ โดยมีรายละเอียดดังนี้ครับ:\n\n⏰ **เวลาเปิดทำการ:**\n- **วันจันทร์ - วันศุกร์:** เวลา 16:00 น. - 20:00 น.\n- **วันเสาร์ - วันอาทิตย์ และวันหยุดนักขัตฤกษ์:** เวลา 08:00 น. - 12:00 น.\n\n🏥 **สถานที่ให้บริการ:**\n- อาคารผู้ป่วยนอก (OPD) ตามสาขาตรวจโรคเฉพาะทางต่างๆ (แนะนำให้โทรนัดหมายล่วงหน้าก่อนเข้ารับบริการที่สายตรงเบอร์ประชาสัมพันธ์ 02-926-9999)";
    }
    if (t.includes('เช็คสิทธิ์') || t.includes('สิทธิการรักษา') || t.includes('บัตรทอง') || t.includes('ประกันสังคม') || t.includes('ข้าราชการ')) {
      return faqsList[4]?.response || "พี่เจ้าหน้าที่หรือผู้ใช้บริการสามารถตรวจสอบสิทธิ์การรักษาพยาบาลเบื้องต้นได้ง่ายๆ ผ่านช่องทางต่อไปนี้ครับ:\n\n🔍 **ช่องทางการตรวจสอบสิทธิ์:**\n1. **ระบบหลักประกันสุขภาพแห่งชาติ (สปสช.):** โทรสายด่วน **1330** หรือตรวจสอบทางเว็บไซต์ nhso.go.th\n2. **แอปพลิเคชัน \"เป๋าตัง\":** เมนู \"กระเป๋าสุขภาพ\"\n3. **จุดบริการตรวจสอบสิทธิ์:** ยื่นบัตรประชาชนตัวจริงที่แผนกตรวจสอบสิทธิ์และเวชระเบียน ชั้น 1 ก่อนเข้ารับการตรวจรักษา\n\n*หากต้องการเปลี่ยนแปลงสิทธิ์ประกันสังคมมายังโรงพยาบาลธรรมศาสตร์ฯ สามารถยื่นเรื่องได้ในช่วงเวลาที่สำนักงานประกันสังคมเปิดให้แจ้งเปลี่ยนสถานพยาบาลประจำปีครับ*";
    }
    if (t.includes('tuh easy app') || t.includes('easy app') || t.includes('แอปโรงพยาบาล') || t.includes('จองคิวตรวจ') || t.includes('ดาวน์โหลดแอป')) {
      return faqsList[5]?.response || "**TUH Easy App** เป็นแอปพลิเคชันอย่างเป็นทางการของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ที่ช่วยอำนวยความสะดวกในการจองคิวตรวจ เลื่อนนัด ชำระเงิน และเช็คประวัติการรักษาพยาบาลครับ\n\n📲 **ช่องทางการดาวน์โหลด:**\n- **iOS (App Store):** ค้นหาคำว่า **\"TUH Easy App\"** หรือสแกน QR Code ณ จุดบริการประชาสัมพันธ์\n- **Android (Google Play Store):** ค้นหาคำว่า **\"TUH Easy App\"** เพื่อดาวน์โหลดและติดตั้ง\n\n🔑 **ขั้นตอนการใช้งานเบื้องต้น:**\n1. ดาวน์โหลดแอปพลิเคชันและเปิดใช้งาน\n2. ลงทะเบียนเข้าสู่ระบบด้วยหมายเลขบัตรประชาชนและเบอร์โทรศัพท์มือถือที่เคยลงทะเบียนไว้กับโรงพยาบาล\n3. สามารถใช้งานบริการจองคิวตรวจ ชำระเงินออนไลน์ และเช็คประวัติสิทธิ์การรักษาได้ทันทีครับ";
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

  const handleLikeMessage = (msgId, likedState) => {
    let msgText = '';
    let userQuery = '';

    // ค้นหาข้อความพร้อมกันในสถานะ sessions ปัจจุบัน
    const currentSession = sessions.find(s => s.id === activeSessionId);
    if (currentSession) {
      const msgIndex = currentSession.messages.findIndex(m => m.id === msgId);
      if (msgIndex !== -1) {
        const msg = currentSession.messages[msgIndex];
        msgText = msg.text;
        if (msgIndex > 0) {
          userQuery = currentSession.messages[msgIndex - 1].text;
        }

        const newLiked = likedState === 'like' ? !msg.liked : false;
        const newDisliked = likedState === 'dislike' ? !msg.disliked : false;

        // ตรวจสอบว่าผู้ใช้กำลังไม่พอใจกับข้อความหรือไม่
        const isDisliking = likedState === 'dislike' && !msg.disliked;
        if (isDisliking) {
          setDislikeQuestion(userQuery || 'ไม่พบคำถาม');
          setDislikeAnswer(msgText);
          setDislikeMsgId(msgId);
          setDislikeReason('');
          setDislikeSuccess(false);
          setShowDislikeModal(true);
        }

        // ส่งบันทึกการให้คะแนนไปยังส่วนหลังบ้าน (เรียกด้านนอกป้องกัน React Strict Mode ดับเบิ้ลรัน)
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
      }
    }

    setSessions(prevSessions => prevSessions.map(s => {
      if (s.id === activeSessionId) {
        return {
          ...s,
          messages: s.messages.map(m => {
            if (m.id === msgId) {
              return {
                ...m,
                liked: likedState === 'like' ? !m.liked : false,
                disliked: likedState === 'dislike' ? !m.disliked : false
              };
            }
            return m;
          })
        };
      }
      return s;
    }));
  };

  const handleCopyMessage = (text, msgId) => {
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

  const handleCloseChatbot = () => {
    const feedbackSubmitted = sessionStorage.getItem('tuh_feedback_submitted');
    if (feedbackSubmitted === 'true') {
      window.location.href = "https://intranet.hospital.tu.ac.th/";
    } else {
      setIsForcedFeedback(true);
      setShowFeedback(true);
    }
  };

  const handleFeedbackSubmit = (e) => {
    e.preventDefault();

    const feedbackData = {
      rating: feedbackRating >= 4 ? 'like' : 'dislike',
      stars: feedbackRating,
      comment: feedbackText,
      query: isForcedFeedback ? 'บังคับกรอกก่อนปิดหน้าต่าง' : 'ความคิดเห็นทั่วไปจากแบบฟอร์ม',
      msgId: `feedback-${Date.now()}`
    };

    fetch(API_URL + '/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    })
      .then(r => r.json())
      .then(data => {
        sessionStorage.setItem('tuh_feedback_submitted', 'true');
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
        setDislikeSuccess(true);
        setTimeout(() => {
          setShowDislikeModal(false);
          setDislikeSuccess(false);
          setDislikeReason('');
        }, 1500);
      });
  };

  const parseMarkdown = (text) => {
    if (!text) return '';
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-tuh-navy dark:text-white">$1</strong>');
    html = html.replace(/^[-\*]\s*(.*?)$/gm, '<li class="ml-4 list-disc">$1</li>');
    html = html.replace(/^\d+\.\s(.*?)$/gm, '<li class="ml-4 list-decimal">$1</li>');
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-tuh-rose dark:text-tuh-coral hover:text-tuh-coral dark:hover:text-tuh-pink underline font-semibold hover:opacity-80 transition">$1 <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i></a>');
    html = html.replace(/\n/g, '<br/>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="h-[100dvh] w-screen p-0 md:p-6 lg:p-8 bg-zayg-gradient box-border overflow-hidden flex font-sans text-tuh-navy dark:text-white transition-colors duration-300">
      <div className="flex-1 flex h-full overflow-hidden bg-white/70 dark:bg-tuh-navy/70 backdrop-blur-md rounded-none md:rounded-[24px] border-0 md:border border-slate-300 dark:border-white/20 shadow-none md:shadow-2xl relative">

        {/* 1. LEFT SIDEBAR PANEL (หน้าต่างซ้าย)  */}
        <Sidebar
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          isDarkMode={isDarkMode}
          setIsDarkMode={setIsDarkMode}
          sidebarWidth={sidebarWidth}
          fontSize={fontSize}
          setFontSize={setFontSize}
          sessions={sessions}
          activeSessionId={activeSessionId}
          setActiveSessionId={setActiveSessionId}
          currentTime={currentTime}
          handleNewChat={handleNewChat}
          handleDeleteSession={handleDeleteSession}
          setShowGuide={setShowGuide}
          setShowFeedback={setShowFeedback}
          setIsForcedFeedback={setIsForcedFeedback}
          startResizing={startResizing}
          startTouchResizing={startTouchResizing}
          logo={logo}
        />

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
                <div className="hidden md:flex items-center gap-2">
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
              <div className="flex-1 w-full overflow-y-auto custom-scrollbar z-10 px-4 md:px-8 pb-8 flex flex-col select-none justify-center">
                <div className="flex flex-col lg:flex-row items-center justify-center gap-6 lg:gap-2 max-w-5xl mx-auto animate-fade-in my-auto py-6 w-full">
                  {/* ส่วนซ้าย: รูปมาสคอตหมาที่ขยายใหญ่ขึ้น */}
                  <div className="flex-shrink-0 flex justify-center items-center order-1 lg:order-1 w-full lg:w-auto">
                    <img
                      src={currentMascot}
                      className={`${isDarkMode
                          ? "w-48 md:w-64 lg:w-72 xl:w-96 max-h-[10rem] md:max-h-[13.75rem] lg:max-h-[18.75rem] xl:max-h-[26.25rem]"
                          : "w-36 md:w-44 lg:w-60 xl:w-80 max-h-[8.125rem] md:max-h-[11.25rem] lg:max-h-[16.25rem] xl:max-h-[23.75rem]"
                        } h-auto object-contain animate-mascot-float mb-3 lg:mb-0`}
                      style={isDarkMode ? {
                        WebkitMaskImage: 'radial-gradient(ellipse at center, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%)',
                        maskImage: 'radial-gradient(ellipse at center, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%)'
                      } : {}}
                      alt="Mascot"
                    />
                  </div>

                  {/* ส่วนขวา: ข้อความ ช่องแชท และ FAQ */}
                  <div className="flex-1 flex flex-col items-center lg:items-start text-center lg:text-left max-w-xl w-full order-2 lg:order-2">
                    <div className="mb-4 max-w-xl leading-relaxed">
                      {welcomeMessage.includes('\n') ? (
                        <>
                          <div className="text-lg md:text-xl lg:text-[22px] lg:leading-8 font-bold text-tuh-navy dark:text-white mb-2">
                            {parseMarkdown(welcomeMessage.split('\n')[0].trim())}
                          </div>
                          <div className="font-medium text-tuh-indigo/80 dark:text-slate-200 font-semibold text-sm md:text-base">
                            {parseMarkdown(welcomeMessage.split('\n').slice(1).join('\n').trim())}
                          </div>
                        </>
                      ) : (
                        <div className="font-medium text-tuh-indigo/80 dark:text-slate-200 font-semibold text-sm md:text-base">
                          {parseMarkdown(welcomeMessage)}
                        </div>
                      )}
                    </div>

                    {/* ช่องรับข้อความส่วนกลางจำลอง */}
                    <div className="w-full flex items-center gap-2 p-1.5 pl-4 rounded-2xl bg-white/70 dark:bg-[#1B2062]/60 border border-white/60 dark:border-white/10 shadow-lg backdrop-blur-md mb-4 focus-within:ring-2 focus-within:ring-tuh-rose/50 transition">
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
                        className="flex-1 bg-transparent border-none outline-none text-tuh-navy dark:text-white placeholder-tuh-indigo/45 dark:placeholder-white/40 font-medium py-2 px-1 text-sm md:text-base"
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
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full">
                      {faqsList.slice(0, 4).map(faq => (
                        <button
                          key={faq.id}
                          onClick={() => {
                            handleSendMessage(faq.question);
                          }}
                          className="flex items-center gap-3 px-4 md:px-5 py-2 md:py-2.5 text-xs md:text-sm font-semibold rounded-2xl bg-white/60 dark:bg-[#1B2062]/40 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-rose/25 dark:hover:text-white border border-slate-200/50 dark:border-white/5 shadow-sm transition-all active:scale-[0.98] w-full text-left"
                        >
                          <i className={`fa-solid ${faq.icon} text-tuh-rose shrink-0`}></i>
                          <span className="leading-snug">{faq.question}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ==================== STATE B: หน้าต่างแชทแบบเต็มหน้าจอ (เมื่อมีการสนทนา) ==================== */
            <div className="w-full h-full flex flex-col bg-white/85 dark:bg-[#1B2062]/85 backdrop-blur-md overflow-hidden z-10 transition-all duration-300 animate-slide-in">
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
                <div className="hidden md:flex w-full lg:w-auto justify-start lg:justify-end shrink-0 pl-12 md:pl-0 lg:pl-0 gap-2">
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
                  activeSession.messages.map((msg, index) => (
                    <MessageBubble
                      key={msg.id || index}
                      msg={msg}
                      index={index}
                      isDarkMode={isDarkMode}
                      copiedId={copiedId}
                      isTyping={isTyping}
                      currentBotAvatar={currentBotAvatar}
                      handleLikeMessage={handleLikeMessage}
                      handleCopyMessage={handleCopyMessage}
                      setInputValue={setInputValue}
                      parseMarkdown={parseMarkdown}
                    />
                  ))
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
              <InputBar
                isActiveSessionLatest={isActiveSessionLatest}
                showFaqs={showFaqs}
                setShowFaqs={setShowFaqs}
                faqsList={faqsList}
                isTyping={isTyping}
                inputValue={inputValue}
                setInputValue={setInputValue}
                handleSendMessage={handleSendMessage}
                handleStopGeneration={handleStopGeneration}
                inputRef={inputRef}
              />
            </div>
          )}
        </main>

        <GuideModal
          showGuide={showGuide}
          setShowGuide={setShowGuide}
          parseMarkdown={parseMarkdown}
        />

        <FeedbackModal
          showFeedback={showFeedback}
          setShowFeedback={setShowFeedback}
          feedbackRating={feedbackRating}
          setFeedbackRating={setFeedbackRating}
          feedbackText={feedbackText}
          setFeedbackText={setFeedbackText}
          feedbackSuccess={feedbackSuccess}
          isForcedFeedback={isForcedFeedback}
          handleFeedbackSubmit={handleFeedbackSubmit}
        />

        <DislikeModal
          showDislikeModal={showDislikeModal}
          setShowDislikeModal={setShowDislikeModal}
          dislikeQuestion={dislikeQuestion}
          dislikeAnswer={dislikeAnswer}
          dislikeReason={dislikeReason}
          setDislikeReason={setDislikeReason}
          dislikeSuccess={dislikeSuccess}
          handleDislikeSubmit={handleDislikeSubmit}
        />

        <AnnouncementModal
          showAnnModal={showAnnModal}
          activeAnnouncements={activeAnnouncements}
          handleCloseAnnModal={handleCloseAnnModal}
          stripHtml={stripHtml}
          formatAnnDate={formatAnnDate}
        />
      </div>
    </div>
  );
}

export default App;
