/**
 * useChat Hook — Chat State Management
 * แยกออกมาจาก App.jsx เพื่อความสะอาดของโค้ด
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { chatAPI, adminAPI } from '../services/api';

export const useChat = (welcomeMessage) => {
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem('tuh_chats');
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    return [createDefaultSession(welcomeMessage)];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const sessions = JSON.parse(localStorage.getItem('tuh_chats') || '[]');
    return sessions?.[0]?.id || 'session-1';
  });

  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef(null);

  // Persist sessions
  useEffect(() => {
    localStorage.setItem('tuh_chats', JSON.stringify(sessions));
    localStorage.setItem('tuh_last_chat_time', Date.now().toString());
  }, [sessions]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  const sendMessage = useCallback(async (query) => {
    if (!query.trim() || isLoading) return;

    const userMsg = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }),
    };

    // Add user message
    setSessions(prev => prev.map(s =>
      s.id === activeSessionId
        ? { ...s, messages: [...s.messages, userMsg] }
        : s
    ));

    setIsLoading(true);

    try {
      const history = activeSession.messages.slice(-10).map(m => ({
        sender: m.sender,
        text: m.text,
      }));

      const { data } = await chatAPI.sendMessage(query, history, activeSessionId);

      const botMsg = {
        id: `msg-${Date.now() + 1}`,
        sender: 'bot',
        text: data.answer,
        citations: data.citations || [],
        formLinks: data.form_links || [],
        usedRag: data.used_rag,
        responseTime: data.response_time,
        model: data.model,
        historyId: data.history_id,
        timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }),
        feedback: null,
      };

      setSessions(prev => prev.map(s =>
        s.id === activeSessionId
          ? { ...s, messages: [...s.messages, botMsg] }
          : s
      ));
    } catch (error) {
      const errorMsg = {
        id: `msg-${Date.now() + 1}`,
        sender: 'bot',
        text: 'เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้งครับ',
        timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }),
      };
      setSessions(prev => prev.map(s =>
        s.id === activeSessionId
          ? { ...s, messages: [...s.messages, errorMsg] }
          : s
      ));
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionId, activeSession, isLoading]);

  const newSession = useCallback((welcomeMsg) => {
    const session = createDefaultSession(welcomeMsg || welcomeMessage);
    setSessions(prev => [session, ...prev]);
    setActiveSessionId(session.id);
  }, [welcomeMessage]);

  const deleteSession = useCallback((sessionId) => {
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== sessionId);
      if (filtered.length === 0) {
        const def = createDefaultSession(welcomeMessage);
        setActiveSessionId(def.id);
        return [def];
      }
      if (activeSessionId === sessionId) {
        setActiveSessionId(filtered[0].id);
      }
      return filtered;
    });
  }, [activeSessionId, welcomeMessage]);

  const submitFeedback = useCallback(async (msgId, historyId, rating, comment = '') => {
    try {
      await adminAPI.submitFeedback({ msgId, historyId, rating, comment });
      setSessions(prev => prev.map(s => ({
        ...s,
        messages: s.messages.map(m =>
          m.id === msgId ? { ...m, feedback: rating } : m
        )
      })));
    } catch (e) {
      console.error('Feedback submit error:', e);
    }
  }, []);

  return {
    sessions,
    activeSessionId,
    activeSession,
    isLoading,
    sendMessage,
    newSession,
    deleteSession,
    setActiveSessionId,
    submitFeedback,
  };
};

function createDefaultSession(welcomeMessage) {
  return {
    id: `session-${Date.now()}`,
    title: 'สอบถามข้อมูลเบื้องต้น',
    createdAt: Date.now(),
    messages: [{
      id: 'm1',
      sender: 'bot',
      text: welcomeMessage || 'สวัสดีครับ TUH Chatbot AI ยินดีให้บริการครับ',
      timestamp: new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }),
    }]
  };
}
