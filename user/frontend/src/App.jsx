import React, { useState, useEffect, useRef } from 'react';
import logo from './logo.png';
import dog from './dog.png';

// Predefined FAQ questions and answers
const FAQS = [
  {
    id: 1,
    question: "แนะนำวิธีดูแลดวงตาเมื่อต้องจ้องหน้าจอคอมพิวเตอร์เป็นเวลานาน",
    icon: "fa-eye-slash",
    response: `สำหรับการดูแลดวงตาระหว่างทำงานหน้าจอคอมพิวเตอร์เป็นเวลานาน ทางงานสารสนเทศและศูนย์จักษุวิทยา รพ.ธรรมศาสตร์เฉลิมพระเกียรติ แนะนำกฎ **20-20-20** ดังนี้ครับ:\n\n1. 👀 **พักสายตา:** ทุกๆ 20 นาที ให้หยุดจ้องหน้าจอคอมพิวเตอร์\n2. 🌳 **มองระยะไกล:** มองออกไปที่วัตถุระยะ 20 ฟุต (ประมาณ 6 เมตร)\n3. ⏱️ **เวลาพัก:** มองเป็นเวลาอย่างน้อย 20 วินาที เพื่อผ่อนคลายกล้ามเนื้อตา\n\nนอกจากนี้ควรปรับความสว่างของหน้าจอให้เหมาะสม (เช่น การสลับใช้โหมดมืด (Dark Mode) สำหรับการถนอมสายตาที่เราออกแบบไว้) ปรับระดับสายตาให้อยู่ห่างจากหน้าจอ 50-70 ซม. และกระพริบตาบ่อยๆ หรือใช้น้ำตาเทียมหยอดตาระหว่างวันหากมีอาการตาแห้งครับ`
  },
  {
    id: 2,
    question: "ขั้นตอนการทำบัตรประจำตัวผู้ป่วยใหม่ต้องใช้เอกสารอะไรบ้าง?",
    icon: "fa-id-card",
    response: `การทำบัตรผู้ป่วยใหม่ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ สามารถทำได้ผ่าน 2 ช่องทางสะดวกดังนี้ครับ:\n\n🌐 **ช่องทางที่ 1: ออนไลน์ (แนะนำและรวดเร็วที่สุด)**\n- ดำเนินการผ่านแอปพลิเคชัน **TUH Easy App** (เมนู: ลงทะเบียนผู้ป่วยใหม่)\n- ถ่ายรูปบัตรประชาชนและใบหน้าเพื่อยืนยันตัวตนล่วงหน้า\n\n🏥 **ช่องทางที่ 2: ดำเนินการที่โรงพยาบาล**\n- ติดต่อที่ **แผนกเวชระเบียน (ตึกผู้ป่วยนอก ชั้น 1 ประตู 1)**\n- **เอกสารที่ต้องใช้:** บัตรประจำตัวประชาชนตัวจริง (สำหรับคนไทย) หรือหนังสือเดินทาง Passport (สำหรับชาวต่างชาติ)\n- กรอกข้อมูลในแบบฟอร์มเปิดสิทธิ์และรอเจ้าหน้าที่ถ่ายรูปทำบัตรประจำตัวผู้ป่วยครับ`
  },
  {
    id: 3,
    question: "ติดต่อศูนย์ไอที (งานสารสนเทศ) รพ.ธรรมศาสตร์ฯ ได้ช่องทางไหนบ้าง?",
    icon: "fa-network-wired",
    response: `ท่านสามารถติดต่อ **งานสารสนเทศ (IT Department)** โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ได้ในวันและเวลาราชการ (จันทร์-ศุกร์ เวลา 08:00 - 16:00 น.) ครับ:\n\n📞 **เบอร์โทรศัพท์ภายใน:** โทร. 02-926-9999 ต่อ 7120 - 7124\n✉️ **อีเมล:** it@tuh.ac.th\n🏢 **สถานที่ตั้ง:** อาคารกิตติวัฒนา ชั้น 4 (แผนกงานสารสนเทศ)\n💻 **แจ้งปัญหาออนไลน์:** สำหรับเจ้าหน้าที่ สามารถสแกนแจ้งผ่านระบบ IT Service Portal บนเครือข่ายอินทราเน็ตโรงพยาบาลได้โดยตรงครับ`
  },
  {
    id: 4,
    question: "เวลาทำการของคลินิกนอกเวลาราชการคือช่วงเวลาใด?",
    icon: "fa-clock",
    response: `**คลินิกนอกเวลาราชการ (Specialty Clinic)** โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ เปิดให้บริการรักษาพยาบาลนอกเวลาปกติเพื่ออำนวยความสะดวกดังนี้ครับ:\n\n📅 **วันจันทร์ - วันศุกร์:** เวลา 16:00 - 20:00 น.\n📅 **วันเสาร์ - วันอาทิตย์ และวันหยุดนักขัตฤกษ์:** เวลา 08:00 - 12:00 น. (บางแผนกคลินิกเฉพาะทางอาจให้บริการถึง 16:00 น.)\n\n📢 *ข้อแนะนำ:* ควรโทรนัดหมายล่วงหน้าที่แผนกที่ต้องการรักษา หรือเบอร์ประชาสัมพันธ์หลัก 02-926-9999 หรือตรวจสอบแพทย์เวรและทำนัดล่วงหน้าผ่านแอปพลิเคชัน **TUH Easy App** ครับ`
  },
  {
    id: 5,
    question: "สามารถตรวจสอบสิทธิ์การรักษาพยาบาล (เช่น บัตรทอง, ประกันสังคม) ได้อย่างไร?",
    icon: "fa-hand-holding-medical",
    response: `การตรวจสอบสิทธิ์การรักษาพยาบาล (บัตรทอง 30 บาท, ประกันสังคม, หรือสิทธิ์ข้าราชการ) สามารถทำได้สะดวกผ่านช่องทางต่อไปนี้ครับ:\n\n1. 📱 **ออนไลน์ด้วยตนเอง (แนะนำ):**\n   - ผ่านแอปพลิเคชัน **เป๋าตัง** (เลือกเมนู กระเป๋าสุขภาพ > สิทธิการรักษาพยาบาล)\n   - ผ่านทาง LINE Official Account ของ สปสช. โดยแอดไลน์ **@nhso** แล้วเลือกเช็คสิทธิ์\n2. 🏥 **ตรวจสอบที่โรงพยาบาล:** นำบัตรประชาชนมาเสียบเช็คสิทธิ์ได้ที่เครื่องบริการอัตโนมัติ (Kiosk) โถงชั้น 1 อาคารผู้ป่วยนอก\n3. ☎️ **โทรสายด่วน สปสช.:** ติดต่อศูนย์บริการหลัก สปสช. โทร. **1330** (เปิดบริการ 24 ชั่วโมง)`
  },
  {
    id: 6,
    question: "ขอลิงก์ดาวน์โหลดแอปพลิเคชัน TUH Easy App สำหรับจองคิวการรักษา",
    icon: "fa-mobile-screen-button",
    response: `แอปพลิเคชัน **TUH Easy App** ช่วยให้ท่านจองคิว เลื่อนนัด ดูประวัติการรักษาพยาบาล ตรวจสอบสิทธิ์การรักษา และชำระเงินออนไลน์ได้อย่างสะดวกรวดเร็วครับ\n\n📲 **ลิงก์ดาวน์โหลดอย่างเป็นทางการ:**\n- 🍏 **สำหรับ iOS (App Store):** [ดาวน์โหลดที่นี่](https://apps.apple.com/th/app/tuh-easy/id1527718210)\n- 🤖 **สำหรับ Android (Google Play Store):** [ดาวน์โหลดที่นี่](https://play.google.com/store/apps/details?id=th.ac.tuh.easyapp)\n\nหากท่านพบปัญหาหรือต้องการคำแนะนำการใช้งานแอป สามารถสอบถามเจ้าหน้าที่บริการที่จุดประชาสัมพันธ์หลักตึกผู้ป่วยนอก ชั้น 1 ได้ครับ`
  }
];

function App() {
  // Theme State (Default to true for Dark Mode as it is softest on the eyes, or Light Mode depending on storage)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_theme');
    if (saved !== null) {
      return saved === 'dark';
    }
    // Default to light mode but customized to soft eyes-friendly tones
    return false;
  });

  // Sidebar resizable width state
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('tuh_sidebar_width');
    return saved ? parseInt(saved, 10) : 320;
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

  // Welcome message state
  const [welcomeMessage, setWelcomeMessage] = useState(() => {
    return localStorage.getItem('tuh_welcome_message') || 'สวัสดีครับ ยินดีต้อนรับสู่ **TUH Chatbot AI** งานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ยินดีให้บริการครับ 😊\n\nท่านต้องการสอบถามข้อมูลด้านใด สามารถพิมพ์สอบถามหรือกดเลือกคำถามยอดนิยมด้านล่างนี้ได้เลยครับ';
  });

  // Chat sessions state
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

    const savedWelcome = localStorage.getItem('tuh_welcome_message') || 'สวัสดีครับ ยินดีต้อนรับสู่ **TUH Chatbot AI** งานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ ยินดีให้บริการครับ 😊\n\nท่านต้องการสอบถามข้อมูลด้านใด สามารถพิมพ์สอบถามหรือกดเลือกคำถามยอดนิยมด้านล่างนี้ได้เลยครับ';

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

    // Check 1-hour inactivity
    const lastChatTime = localStorage.getItem('tuh_last_chat_time');
    const now = Date.now();
    const oneHourInMs = 60 * 60 * 1000;
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

    // Filter out sessions older than 7 days (7 * 24 * 60 * 60 * 1000 = 604,800,000 ms)
    const sevenDaysInMs = 7 * 24 * 60 * 60 * 1000;

    const validSessions = loadedSessions.map(session => {
      // If session doesn't have createdAt, try to parse from the ID, or default to current time
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
    }).filter(session => {
      return (now - session.createdAt) <= sevenDaysInMs;
    });

    if (validSessions.length === 0) {
      return [defaultSession];
    }

    // Check if the most recent session has messages
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
            text: 'สวัสดีครับ! เริ่มต้นบทสนทนาใหม่แล้วครับ ท่านต้องการสอบถามข้อมูลส่วนใดของโรงพยาบาลธรรมศาสตร์ฯ หรือมีข้อขัดข้องเกี่ยวกับระบบสารสนเทศส่วนใด ถามเข้ามาได้เลยครับ 🏥🤖',
            timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
          }
        ]
      };

      // Store the active session ID in window so the activeSessionId useState can pick it up
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showFaqs, setShowFaqs] = useState(true);
  const [copiedId, setCopiedId] = useState(null);
  const [faqsList, setFaqsList] = useState(FAQS);
  
  // Feedback form state
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [isForcedFeedback, setIsForcedFeedback] = useState(false);

  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Sync theme with HTML class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tuh_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tuh_theme', 'light');
    }
  }, [isDarkMode]);
  // Save sessions to localStorage
  useEffect(() => {
    localStorage.setItem('tuh_chats', JSON.stringify(sessions));
  }, [sessions]);

  // Inactivity checker: Check every 30 seconds if last chat activity was more than 1 hour ago
  useEffect(() => {
    const defaultSession = {
      id: 'session-1',
      title: 'สอบถามข้อมูลเบื้องต้น',
      createdAt: Date.now(),
      messages: [
        {
          id: 'm1',
          sender: 'bot',
          text: welcomeMessage,
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        }
      ]
    };

    const checkInactivity = () => {
      const lastChatTime = localStorage.getItem('tuh_last_chat_time');
      if (lastChatTime) {
        const now = Date.now();
        const oneHourInMs = 60 * 60 * 1000;
        if (now - parseInt(lastChatTime, 10) > oneHourInMs) {
          console.log("Inactivity detected (> 1 hour). Clearing chat history.");
          localStorage.removeItem('tuh_chats');
          localStorage.removeItem('tuh_last_chat_time');
          setSessions([defaultSession]);
          setActiveSessionId('session-1');
        }
      }
    };

    // Run check immediately on mount/update
    checkInactivity();

    const interval = setInterval(checkInactivity, 30000);
    return () => clearInterval(interval);
  }, [welcomeMessage]);

  // Load custom welcome message and configurations on startup
  useEffect(() => {
    fetch('http://localhost:8000/api/admin/settings')
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

  // Listen to beforeunload to prevent tab closing without feedback
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      const feedbackSubmitted = sessionStorage.getItem('tuh_feedback_submitted');
      if (feedbackSubmitted !== 'true') {
        e.preventDefault();
        e.returnValue = 'กรุณากรอกข้อเสนอแนะการใช้งานก่อนปิดระบบแชทบอท';
        return 'กรุณากรอกข้อเสนอแนะการใช้งานก่อนปิดระบบแชทบอท';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  // Automatically show/hide FAQs based on messages in current chat when activeSessionId changes
  useEffect(() => {
    const session = sessions.find(s => s.id === activeSessionId);
    if (session) {
      setShowFaqs(session.messages.length <= 1);
    }
  }, [activeSessionId]);

  // Auto scroll to chat bottom
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

    // Scroll immediately
    scrollToBottom();

    // Scroll again after short delays to account for DOM rendering,
    // layout updates, and message bubble transition animations.
    const timer1 = setTimeout(scrollToBottom, 100);
    const timer2 = setTimeout(scrollToBottom, 300);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [sessions, activeSessionId, isTyping]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0] || { messages: [] };

  // Create new conversation
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
          text: 'สวัสดีครับ! เริ่มต้นบทสนทนาใหม่แล้วครับ ท่านต้องการสอบถามข้อมูลส่วนใดของโรงพยาบาลธรรมศาสตร์ฯ หรือมีข้อขัดข้องเกี่ยวกับระบบสารสนเทศส่วนใด ถามเข้ามาได้เลยครับ 🏥🤖',
          timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
        }
      ]
    };
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newId);
    setIsSidebarOpen(false);
  };

  // Delete chat session
  const handleDeleteSession = (id, e) => {
    e.stopPropagation();
    if (sessions.length === 1) {
      alert("ไม่สามารถลบการสนทนาทั้งหมดได้ ต้องมีอย่างน้อย 1 รายการ");
      return;
    }
    const filtered = sessions.filter(s => s.id !== id);
    setSessions(filtered);
    if (activeSessionId === id) {
      setActiveSessionId(filtered[0].id);
    }
  };

  // Process and send user message
  const handleSendMessage = (text) => {
    if (!text.trim()) return;

    localStorage.setItem('tuh_last_chat_time', Date.now().toString());

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })
    };

    // Extract recent short-term history (up to last 2 turns / 4 messages)
    const sessionMessages = activeSession.messages || [];
    const startIndex = (sessionMessages.length > 0 && sessionMessages[0].sender === 'bot') ? 1 : 0;
    const candidates = sessionMessages.slice(startIndex);
    const recentHistory = candidates.slice(-4).map(m => ({
      sender: m.sender,
      text: m.text
    }));

    // Update active session messages
    let updatedSessions = sessions.map(s => {
      if (s.id === activeSessionId) {
        // Update session title based on first user message if it was a default title
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

    // Call the Python Hybrid Search API (FAISS + BM25)
    fetch('http://localhost:8000/api/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({
        query: text,
        top_k: 2,
        history: recentHistory
      })
    })
    .then(response => {
      if (!response.ok) throw new Error("HTTP error " + response.status);
      return response.json();
    })
    .then(data => {
      // Use the generated AI answer from the backend if available
      const botResponseText = data.answer || getBotResponse(text);

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
    })
    .catch(error => {
      console.warn("API Search failed, using static fallback:", error);
      // Fallback on error
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
    });
  };

  // Custom Bot Response Router
  const getBotResponse = (text) => {
    const t = text.toLowerCase().trim();
    
    // Check match against predefined FAQs
    for (const faq of faqsList) {
      if (t === faq.question.toLowerCase().trim() || t.includes(faq.question.substring(0, 20).toLowerCase())) {
        if (faq.response && faq.response.trim() !== '') {
          return faq.response;
        }
      }
    }


    // Keyword logic
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

    // Default Fallback
    return `ขอบคุณสำหรับคำถามครับคุณผู้ใช้ ผมเป็นระบบปัญญาประดิษฐ์ให้ข้อมูลเบื้องต้นของโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ สำหรับคำถามเกี่ยวกับการรักษาเฉพาะทางลึกหรือข้อมูลอื่นๆ นอกเหนือจากนี้ ท่านสามารถติดต่อเพิ่มเติมได้ที่:\n\n` +
      `📞 **สายด่วนโรงพยาบาล (ประชาสัมพันธ์):** โทร. 02-926-9999\n` +
      `🏢 **งานสารสนเทศ (ไอที):** โทร. 02-926-9999 ต่อ 7120\n\n` +
      `ท่านสามารถส่งความคิดเห็นและข้อแนะนำการบริการผ่านเมนู **"ข้อเสนอแนะ"** ที่มุมซ้ายล่างได้เลยครับ เพื่อให้ทีมงานสารสนเทศนำไปปรับปรุงระบบแชทบอทให้ตอบคำถามได้หลากหลายและดียิ่งขึ้นครับ`;
  };

  // Handle like/dislike bot messages
  const handleLikeMessage = (msgId, likedState) => {
    let msgText = '';
    let userQuery = '';

    setSessions(prevSessions => prevSessions.map(s => {
      if (s.id === activeSessionId) {
        // Track the message text and search query
        const msgIndex = s.messages.findIndex(m => m.id === msgId);
        if (msgIndex !== -1) {
          msgText = s.messages[msgIndex].text;
          if (msgIndex > 0) {
            userQuery = s.messages[msgIndex - 1].text;
          }
        }

        return {
          ...s,
          messages: s.messages.map(m => {
            if (m.id === msgId) {
              const newLiked = likedState === 'like' ? !m.liked : false;
              const newDisliked = likedState === 'dislike' ? !m.disliked : false;

              // Send rating log to backend
              fetch('http://localhost:8000/api/admin/feedback/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  msgId: msgId,
                  rating: newLiked ? 'like' : (newDisliked ? 'dislike' : ''),
                  comment: '',
                  query: userQuery || msgText.substring(0, 30)
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

  // Handle copy message text
  const handleCopyMessage = (text, msgId) => {
    // Remove markdown bold syntax and link syntax for clean plain text while keeping newlines
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

  // Handle close chatbot
  const handleCloseChatbot = () => {
    const feedbackSubmitted = sessionStorage.getItem('tuh_feedback_submitted');
    if (feedbackSubmitted === 'true') {
      window.location.href = "https://intranet.hospital.tu.ac.th/";
    } else {
      setIsForcedFeedback(true);
      setShowFeedback(true);
    }
  };

  // Handle submit feedback
  const handleFeedbackSubmit = (e) => {
    e.preventDefault();

    // Create feedback record
    const feedbackData = {
      rating: feedbackRating >= 4 ? 'like' : 'dislike',
      comment: feedbackText,
      query: isForcedFeedback ? 'บังคับกรอกก่อนปิดหน้าต่าง' : 'ความคิดเห็นทั่วไปจากแบบฟอร์ม',
      msgId: `feedback-${Date.now()}`
    };

    // Send to backend API
    fetch('http://localhost:8000/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    })
    .then(r => r.json())
    .then(data => {
      sessionStorage.setItem('tuh_feedback_submitted', 'true');
      // Also save locally
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

  // Convert raw message text into HTML with simple Markdown parsing
  const parseMarkdown = (text) => {
    if (!text) return '';
    // Bold parsing (**text**)
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-tuh-navy dark:text-white">$1</strong>');
    // Bullet list items (- item)
    html = html.replace(/^\- (.*?)$/gm, '<li class="ml-4 list-disc">$1</li>');
    // Number list items (1. item)
    html = html.replace(/^\d+\.\s(.*?)$/gm, '<li class="ml-4 list-decimal">$1</li>');
    // Link parsing [text](url)
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-tuh-rose dark:text-tuh-coral hover:text-tuh-coral dark:hover:text-tuh-pink underline font-semibold hover:opacity-80 transition">$1 <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i></a>');
    // Replace newlines with <br/>
    html = html.replace(/\n/g, '<br/>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-tuh-navy dark:bg-[#100220] dark:text-white transition-colors duration-300 font-sans">
      
      {/* 1. LEFT SIDEBAR PANEL (หน้าต่างซ้าย) */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 md:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      
      <aside 
        style={{ '--sidebar-width': `${sidebarWidth}px` }}
        className={`fixed inset-y-0 left-0 z-30 w-80 flex flex-col border-r border-slate-200 dark:border-tuh-purple/20 bg-white dark:bg-tuh-indigo/90 backdrop-blur-md shadow-sm transition-transform duration-300 ease-in-out md:static md:relative md:translate-x-0 tuh-resizable-sidebar ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        
        {/* Sidebar Header */}
        <div className="p-4 border-b border-slate-100 dark:border-tuh-purple/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a 
              href="https://intranet.hospital.tu.ac.th/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-sm overflow-hidden p-0.5 border border-slate-100 dark:border-tuh-purple/10 shrink-0 group/logo cursor-pointer hover:shadow-md transition-all active:scale-95"
              title="ไปยังหน้าอินทราเน็ตโรงพยาบาล"
            >
              <img src={logo} alt="TUH Logo" className="w-full h-full object-contain transition-transform duration-500 group-hover/logo:rotate-[360deg] group-hover/logo:scale-110" />
            </a>
            <div>
              <h2 className="font-extrabold text-lg text-tuh-navy dark:text-white tracking-tight leading-none">TUH</h2>
              <span className="text-xs text-tuh-indigo/60 dark:text-slate-300 font-medium block mt-0.5">Thammasat University Hospital</span>
            </div>
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden p-2 rounded-xl text-tuh-indigo/40 hover:text-tuh-navy dark:text-slate-300 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo transition active:scale-95"
            title="ปิดเมนู"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        {/* Start New Chat Button */}
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-tuh-gradient-2 hover:shadow-lg hover:shadow-tuh-rose/30 hover:scale-[1.02] text-white font-semibold transition-all duration-300 active:scale-[0.98] group"
          >
            <i className="fa-solid fa-plus transition-transform duration-300 group-hover:rotate-90 group-hover:scale-110"></i>
            เริ่มบทสนทนาใหม่
          </button>
        </div>

        {/* Chat History List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 custom-scrollbar">
          <span className="px-3 text-[13px] font-bold text-tuh-indigo/50 dark:text-slate-450 uppercase tracking-wider block mb-2">
            ประวัติการสนทนา
          </span>
          <div className="space-y-1">
            {sessions.map(s => {
              const isActive = s.id === activeSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => {
                    setActiveSessionId(s.id);
                    setIsSidebarOpen(false);
                  }}
                  className={`w-full group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all duration-200 ${
                    isActive
                      ? 'tuh-sidebar-active'
                      : 'tuh-sidebar-inactive'
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <i className={`fa-solid ${isActive ? 'fa-message text-tuh-rose dark:text-tuh-coral' : 'fa-comment text-tuh-indigo/40 dark:text-slate-400'} text-sm shrink-0`}></i>
                    <span className="text-[15px] truncate pr-2">{s.title}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-red-500 p-1 rounded-md text-tuh-indigo/40 dark:text-slate-400 hover:bg-tuh-indigo/20 transition-all shrink-0"
                    title="ลบการสนทนานี้"
                  >
                    <i className="fa-solid fa-trash-can text-xs"></i>
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Menu Buttons */}
        <div className="p-4 border-t border-slate-100 dark:border-tuh-purple/20 space-y-2 bg-slate-50/50 dark:bg-tuh-navy/40">
          
          {/* Theme Mode Toggle (ปรับโหมดหน้าจอ) */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
          >
            <div className="flex items-center gap-3">
              <i className={`fa-solid ${isDarkMode ? 'fa-sun text-amber-500' : 'fa-moon text-tuh-rose'} text-base transition-transform duration-300 group-hover:scale-120 group-hover:rotate-12`}></i>
              <span className="text-[15px] font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">ปรับโหมดหน้าจอ</span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200/60 dark:bg-white/10 text-tuh-navy/60 dark:text-slate-200 font-semibold group-hover:bg-tuh-rose/10 group-hover:text-tuh-rose dark:group-hover:text-white transition-all">
              {isDarkMode ? 'โหมดสว่าง' : 'โหมดมืด'}
            </span>
          </button>

          {/* User Guide Button (คู่มือการใช้งาน) */}
          <button
            onClick={() => { setShowGuide(true); setIsSidebarOpen(false); }}
            className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
          >
            <i className="fa-solid fa-book-open text-tuh-purple dark:text-purple-300 text-base transition-transform duration-300 group-hover:scale-120 group-hover:-rotate-6"></i>
            <span className="text-[15px] font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">คู่มือการใช้งาน</span>
          </button>

          {/* Feedback Button (ข้อเสนอแนะ) */}
          <button
            onClick={() => { setIsForcedFeedback(false); setShowFeedback(true); setIsSidebarOpen(false); }}
            className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all duration-300 hover:translate-x-1 active:scale-[0.98] group"
          >
            <i className="fa-solid fa-comment-dots text-tuh-purple dark:text-purple-300 text-base transition-transform duration-300 group-hover:scale-120 group-hover:translate-y-[-2px]"></i>
            <span className="text-[15px] font-medium group-hover:text-tuh-rose dark:group-hover:text-tuh-pink transition-colors">ข้อเสนอแนะ</span>
          </button>

        </div>
        
        {/* Resize Handle (All Devices - mouse and touch) */}
        <div 
          onMouseDown={startResizing}
          onTouchStart={startTouchResizing}
          className="absolute top-0 right-0 bottom-0 w-3 -mr-1.5 cursor-col-resize z-50 group"
          title="ลากเพื่อปรับขนาดเมนู"
        >
          <div className="w-1 h-full mx-auto bg-transparent group-hover:bg-tuh-rose/40 dark:group-hover:bg-tuh-purple/40 transition-colors duration-150" />
        </div>
      </aside>

      {/* 2. RIGHT CHAT WINDOW PANEL (หน้าต่างขวา) */}
      <main className="flex-1 flex flex-col h-full bg-slate-50 dark:bg-tuh-navy transition-colors duration-300 relative">
        
        {/* Dynamic Background Design Elements from User Image Palette */}
        <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/10 dark:bg-tuh-purple/20 blur-[100px] pointer-events-none animate-float-slow"></div>
        <div className="absolute bottom-40 left-10 w-96 h-96 rounded-full bg-tuh-coral/10 dark:bg-tuh-rose/10 blur-[120px] pointer-events-none animate-float-slower"></div>

        {/* Chat Window Headers */}
        <header className="p-4 md:p-5 border-b border-slate-200 dark:border-tuh-purple/20 bg-white/75 dark:bg-tuh-indigo/40 backdrop-blur-md flex flex-col lg:flex-row gap-3 lg:gap-0 items-start lg:items-center justify-between z-10">
          <div className="flex items-center gap-3 w-full lg:w-auto">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2.5 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-tuh-indigo/50 transition active:scale-95 shrink-0"
              title="เปิดเมนู"
            >
              <i className="fa-solid fa-bars text-lg"></i>
            </button>
            <div className="min-w-0 flex-1 lg:flex-initial">
              <h1 className="text-xl md:text-2xl font-extrabold tracking-tight text-tuh-navy dark:text-white flex items-center gap-2">
                <span className="text-tuh-coral shrink-0"><i className="fa-solid fa-circle-nodes"></i></span>
                <span className="text-tuh-gradient font-black truncate">TUH Chatbot AI</span>
              </h1>
              <p className="text-xs md:text-sm text-tuh-indigo/70 dark:text-slate-300 mt-0.5 md:mt-1 font-semibold text-left truncate">
                งานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
              </p>
            </div>
          </div>
          <div className="w-full lg:w-auto flex justify-start lg:justify-end shrink-0 pl-12 md:pl-0 lg:pl-0 gap-2">
            <span className="text-xs md:text-sm font-semibold text-tuh-indigo/80 dark:text-slate-200 bg-slate-100 dark:bg-tuh-indigo/40 px-3 py-1.5 md:py-2 rounded-xl border border-slate-200/60 dark:border-tuh-purple/20 flex items-center gap-1.5 shadow-sm">
              <i className="fa-solid fa-phone text-tuh-rose animate-pulse text-xs md:text-sm"></i>
              พบปัญหาติดต่อ 8471 หรือ 8343
            </span>

          </div>
        </header>

        {/* Chat Messages Feed Area */}
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-6 py-6 space-y-4 custom-scrollbar z-10"
        >
          
          {activeSession.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto my-auto space-y-4">
              <div className="w-16 h-16 rounded-3xl bg-tuh-pink/20 dark:bg-tuh-indigo/60 flex items-center justify-center text-tuh-rose dark:text-tuh-pink text-3xl shadow-sm">
                <i className="fa-solid fa-comments"></i>
              </div>
              <h3 className="text-lg font-bold text-tuh-navy dark:text-white">เริ่มการสนทนาของคุณ</h3>
              <p className="text-sm text-tuh-indigo/70 dark:text-tuh-pink/70">
                เลือกหัวข้อคำถามที่พบบ่อยด้านล่าง หรือพิมพ์คำถามที่ท่านต้องการทราบเกี่ยวกับบริการโรงพยาบาลธรรมศาสตร์ฯ และแผนกไอที
              </p>
            </div>
          ) : (
            activeSession.messages.map((msg, index) => {
              const isBot = msg.sender === 'bot';
              return (
                <div
                  key={msg.id || index}
                  className={`flex gap-3 max-w-[85%] md:max-w-[75%] ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'} animate-slide-in`}
                >
                  {/* Avatar Icon */}
                  {isBot ? (
                    <img 
                      src={dog} 
                      alt="Dog Bot Icon" 
                      className="w-8 h-8 rounded-lg object-cover shrink-0 shadow-sm transition-transform duration-300 hover:scale-110" 
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs shrink-0 shadow-sm text-white transition-transform duration-300 hover:scale-110 bg-tuh-gradient-1">
                      <i className="fa-solid fa-user"></i>
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div className="space-y-1">
                    <div className={`p-4 rounded-2xl text-[16px] leading-relaxed shadow-sm ${
                      isBot
                        ? 'bg-slate-100 dark:bg-[#07010f] border border-slate-200 dark:border-tuh-purple/30 text-tuh-navy dark:text-white rounded-tl-sm transition-all duration-300 hover:border-tuh-rose/30 dark:hover:border-tuh-purple/50'
                        : 'bg-[#f8bbd0] text-black dark:bg-[#ad1457] dark:text-white border-none rounded-tr-sm shadow-md shadow-[#f8bbd0]/30 dark:shadow-[#ad1457]/20 transition-all duration-300 hover:shadow-lg'
                    }`}>
                      {parseMarkdown(msg.text)}
                    </div>
                    
                    {isBot ? (
                      <div className="flex items-center gap-1.5 mt-1 px-1">
                        {/* Like Button */}
                        <button
                          onClick={() => handleLikeMessage(msg.id, 'like')}
                          className={`p-1.5 rounded-lg text-xs transition-all active:scale-90 ${
                            msg.liked
                              ? 'text-emerald-500 bg-emerald-500/15 dark:bg-emerald-500/25'
                              : 'text-tuh-indigo/40 dark:text-tuh-pink/40 hover:text-emerald-500 hover:bg-emerald-500/10 dark:hover:bg-emerald-500/20'
                          }`}
                          title="ถูกใจ"
                        >
                          <i className={`fa-thumbs-up ${msg.liked ? 'fa-solid' : 'fa-regular'}`}></i>
                        </button>

                        {/* Dislike Button */}
                        <button
                          onClick={() => handleLikeMessage(msg.id, 'dislike')}
                          className={`p-1.5 rounded-lg text-xs transition-all active:scale-90 ${
                            msg.disliked
                              ? 'text-red-500 bg-red-500/10 dark:bg-red-500/20'
                              : 'text-tuh-indigo/40 dark:text-tuh-pink/40 hover:text-red-500 hover:bg-red-500/10 dark:hover:bg-red-500/20'
                          }`}
                          title="ไม่ถูกใจ"
                        >
                          <i className={`fa-thumbs-down ${msg.disliked ? 'fa-solid' : 'fa-regular'}`}></i>
                        </button>

                        {/* Copy Button */}
                        <button
                          onClick={() => handleCopyMessage(msg.text, msg.id)}
                          className={`p-1.5 rounded-lg text-xs transition-all active:scale-90 flex items-center gap-1 ${
                            copiedId === msg.id
                              ? 'text-emerald-600 bg-emerald-500/10 dark:bg-emerald-500/20'
                              : 'text-tuh-indigo/40 dark:text-tuh-pink/40 hover:text-emerald-600 hover:bg-emerald-500/10 dark:hover:bg-emerald-500/20'
                          }`}
                          title="คัดลอกข้อความ"
                        >
                          <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`}></i>
                          {copiedId === msg.id && <span className="text-[10px] font-bold">คัดลอกแล้ว</span>}
                        </button>
                        
                        {/* Dot separator */}
                        <span className="text-[10px] text-tuh-indigo/30 dark:text-tuh-pink/30">•</span>
                        
                        {/* Timestamp */}
                        <span className="text-xs text-tuh-indigo/50 dark:text-tuh-pink/50 font-medium">
                          {msg.timestamp}
                        </span>
                      </div>
                    ) : (
                      /* User Action Bar & Timestamp */
                      <div className="flex items-center justify-end gap-1.5 mt-1 px-1">
                        <span className="text-xs text-tuh-indigo/50 dark:text-tuh-pink/50 font-medium">
                          {msg.timestamp}
                        </span>
                        <span className="text-[10px] text-tuh-indigo/30 dark:text-tuh-pink/30">•</span>
                        <button
                          onClick={() => {
                            setInputValue(msg.text);
                            setTimeout(() => {
                              const textarea = document.querySelector('textarea');
                              if (textarea) {
                                textarea.focus();
                                textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
                              }
                            }, 50);
                          }}
                          className="p-1 rounded-lg text-xs text-tuh-indigo/40 dark:text-tuh-pink/40 hover:text-orange-500 hover:bg-orange-500/10 dark:hover:text-orange-400 dark:hover:bg-orange-500/20 transition-all active:scale-90 flex items-center gap-1 cursor-pointer"
                          title="ย้อนคำถามนี้เพื่อพิมพ์หรือถามใหม่"
                        >
                          <i className="fa-solid fa-arrow-rotate-left"></i>
                          <span className="text-[10px] font-bold">ถามใหม่</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex gap-3 max-w-[75%] mr-auto animate-slide-in">
              <img 
                src={dog} 
                alt="Dog Bot Icon" 
                className="w-8 h-8 rounded-lg object-cover shrink-0 shadow-sm" 
              />
              <div className="bg-slate-100 dark:bg-[#07010f] border border-slate-200 dark:border-tuh-purple/30 p-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2.5 h-2.5 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2.5 h-2.5 rounded-full bg-tuh-rose/60 dark:bg-tuh-pink/60 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Dynamic FAQs and Message Input Panel */}
        <div className="p-5 border-t border-slate-200 dark:border-tuh-purple/20 bg-white/70 dark:bg-tuh-navy/40 backdrop-blur-md z-10">
          
          {/* FAQ Area (คำถามที่พบบ่อย 6 คำถาม) */}
          <div className="mb-4 max-w-4xl mx-auto">
            <button
              onClick={() => setShowFaqs(!showFaqs)}
              className="w-full flex items-center justify-between text-left mb-2 group focus:outline-none"
            >
              <span className="text-sm font-bold text-tuh-indigo/60 dark:text-tuh-pink/60 uppercase tracking-wider flex items-center gap-2 group-hover:text-tuh-rose dark:group-hover:text-white transition-colors">
                <i className="fa-solid fa-circle-question text-tuh-rose transition-transform duration-500 group-hover:rotate-[360deg]"></i>
                คำถามที่พบบ่อย
                <span className="normal-case text-xs font-normal text-tuh-navy/60 dark:text-tuh-pink/60 bg-slate-100 dark:bg-tuh-indigo/60 px-2 py-0.5 rounded-full ml-1 transition-all group-hover:bg-tuh-rose/10 group-hover:text-tuh-rose dark:group-hover:text-white">
                  {showFaqs ? 'คลิกเพื่อซ่อน' : 'คลิกเพื่อแสดง'}
                </span>
              </span>
              <span className="text-tuh-indigo/40 dark:text-tuh-pink/40 group-hover:text-tuh-rose dark:group-hover:text-white transition-colors">
                <i className={`fa-solid fa-chevron-down text-xs transition-transform duration-300 ${showFaqs ? 'rotate-180' : ''}`}></i>
              </span>
            </button>
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-2 overflow-hidden transition-all duration-300 ease-in-out ${
              showFaqs ? 'max-h-[350px] opacity-100 mt-2' : 'max-h-0 opacity-0 pointer-events-none'
            }`}>
              {faqsList.map(faq => (
                <button
                  key={faq.id}
                  onClick={() => handleSendMessage(faq.question)}
                  className="flex items-center gap-3 p-3 text-left rounded-xl bg-white dark:bg-tuh-indigo/45 hover:bg-tuh-pink/5 dark:hover:bg-tuh-indigo/75 border border-slate-200 dark:border-tuh-purple/25 text-sm font-semibold text-tuh-navy dark:text-tuh-pink/90 transition-all duration-300 hover:translate-y-[-2px] hover:shadow-md hover:border-tuh-rose/40 dark:hover:border-tuh-purple/45 active:scale-[0.99] group"
                >
                  <span className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-tuh-indigo/60 flex items-center justify-center text-tuh-rose dark:text-tuh-pink shrink-0 text-xs transition-all duration-300 group-hover:bg-tuh-rose group-hover:text-white">
                    <i className={`fa-solid ${faq.icon} transition-transform duration-300 group-hover:scale-110`}></i>
                  </span>
                  <span className="truncate transition-colors duration-200 group-hover:text-tuh-rose dark:group-hover:text-tuh-pink">{faq.question}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Question Input Box (ช่องคำถาม) */}
          <div className="max-w-4xl mx-auto flex items-end gap-2 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(inputValue);
                }
              }}
              rows={Math.min(4, inputValue.split('\n').length)}
              placeholder="พิมพ์คำถามหรือพิมพ์แจ้งปัญหาไอทีที่นี่..."
              className="flex-1 py-3 pl-4 pr-12 rounded-2xl bg-slate-100 dark:bg-[#07010f] border border-slate-350 dark:border-tuh-purple/30 text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-slate-450 focus:outline-none focus:ring-2 focus:ring-tuh-rose dark:focus:ring-tuh-purple focus:border-transparent text-[16px] transition shadow-inner resize-none overflow-y-auto leading-relaxed"
            />
            <button
              onClick={() => handleSendMessage(inputValue)}
              className="absolute right-2 bottom-1.5 p-2.5 rounded-xl bg-tuh-gradient-2 hover:shadow-[0_0_12px_rgba(255,77,128,0.4)] text-white transition-all hover:scale-[1.06] active:scale-[0.98] shadow-md shadow-tuh-rose/25 group"
              title="ส่งคำถาม"
            >
              <i className="fa-solid fa-paper-plane text-sm transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:rotate-[15deg]"></i>
            </button>
          </div>
        </div>

      </main>

      {/* 3. MODAL: USER MANUAL (คู่มือการใช้งาน) */}
      {showGuide && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full max-h-[85vh] flex flex-col border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
            {/* Modal Header */}
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
            
            {/* Modal Content */}
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

            {/* Modal Footer */}
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

      {/* 4. MODAL: FEEDBACK (ข้อเสนอแนะ) */}
      {showFeedback && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
            {/* Modal Header */}
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
            
            {/* Modal Form Content */}
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
                
                {/* Star Rating Select */}
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
                        <i className={`fa-solid fa-star ${star <= feedbackRating ? 'text-amber-400' : 'text-slate-200 dark:text-tuh-indigo/60'}`}></i>
                      </button>
                    ))}
                    <span className="text-xs text-tuh-indigo/40 dark:text-tuh-pink/40 font-bold ml-2">
                      ({feedbackRating} คะแนน)
                    </span>
                  </div>
                </div>

                {/* Message Text area */}
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

                {/* Form Footer Buttons */}
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

    </div>
  );
}

export default App;
