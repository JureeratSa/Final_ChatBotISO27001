/**
 * TUH Chatbot AI v2 — Main App.jsx
 * Orchestrates all components. Significantly smaller than original 111KB version.
 * Auth context, theme, routing between User Chat and Admin views.
 */
import React, { useState, useEffect, Suspense, lazy } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { chatAPI } from './services/api';
import { useChat } from './hooks/useChat';
import logo from './logo.png';
import dog from './dog.png';
import dog_light from './dog_light.png';
import botAvatar from './bot_avatar.jpg';

// Lazy-load heavy components
const MessageBubble = lazy(() => import('./components/Chat/MessageBubble'));
const InputBar = lazy(() => import('./components/Chat/InputBar'));
const AdminLogin = lazy(() => import('./components/Admin/AdminLogin'));

// ─── Theme & Font Size Context ─────────────────────────────────────────────────
function AppContent() {
  const { isAuthenticated, user, logout, isLoading: authLoading } = useAuth();

  // ─── Theme ────────────────────────────────────────────────────────────────
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_theme');
    return saved ? saved === 'dark' : false;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
    localStorage.setItem('tuh_theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  // ─── View State ───────────────────────────────────────────────────────────
  const [view, setView] = useState('chat'); // 'chat' | 'admin-login' | 'admin'
  const [publicSettings, setPublicSettings] = useState(null);

  // Load public settings
  useEffect(() => {
    chatAPI.getPublicSettings()
      .then(({ data }) => setPublicSettings(data))
      .catch(() => {});
  }, []);

  // ─── Chat Hook ─────────────────────────────────────────────────────────────
  const {
    sessions, activeSessionId, activeSession, isLoading,
    sendMessage, newSession, deleteSession, setActiveSessionId, submitFeedback
  } = useChat(publicSettings?.welcome_message);

  // ─── Sidebar Width (resizable) ─────────────────────────────────────────────
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    return parseInt(localStorage.getItem('tuh_sidebar_width') || '320', 10);
  });

  const currentMascot = isDarkMode ? dog : dog_light;

  if (authLoading) {
    return (
      <div className="min-h-screen bg-zayg-gradient flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-zayg-gradient flex overflow-hidden ${isDarkMode ? 'dark' : ''}`}>
      <Suspense fallback={
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      }>
        {view === 'admin-login' && !isAuthenticated ? (
          <AdminLogin onLoginSuccess={() => setView('admin')} />
        ) : (
          <>
            {/* ─── Sidebar ─────────────────────────────────────────────────── */}
            <div
              className="tuh-resizable-sidebar glass-panel border-r border-white/20 dark:border-white/5 flex flex-col"
              style={{ '--sidebar-width': `${sidebarWidth}px` }}
            >
              {/* Logo */}
              <div className="p-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                  <img src={logo} alt="TUH Logo" className="w-10 h-10 object-contain" />
                  <div>
                    <h1 className="font-bold text-slate-800 dark:text-slate-100 text-sm leading-tight">
                      TUH Chatbot AI
                    </h1>
                    <p className="text-xs text-slate-500">โรงพยาบาลธรรมศาสตร์ฯ</p>
                  </div>
                </div>
              </div>

              {/* New Chat Button */}
              <div className="p-3">
                <button
                  id="new-chat-btn"
                  onClick={() => newSession(publicSettings?.welcome_message)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 bg-tuh-gradient-1 text-white rounded-xl text-sm font-medium shadow-sm hover:shadow-md active:scale-[0.98] transition-all"
                >
                  <i className="fas fa-plus text-xs" />
                  บทสนทนาใหม่
                </button>
              </div>

              {/* Session List */}
              <div className="flex-1 overflow-y-auto custom-scrollbar px-2 py-1 space-y-1">
                {sessions.map(session => (
                  <button
                    key={session.id}
                    onClick={() => setActiveSessionId(session.id)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-all group flex items-center justify-between
                      ${session.id === activeSessionId ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive'}`}
                  >
                    <span className="truncate flex-1">
                      <i className="fas fa-comment-dots mr-2 text-xs opacity-60" />
                      {session.title || 'บทสนทนา'}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteSession(session.id); }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all text-xs"
                    >
                      <i className="fas fa-times" />
                    </button>
                  </button>
                ))}
              </div>

              {/* Bottom Controls */}
              <div className="p-3 border-t border-white/10 flex items-center gap-2">
                <button
                  onClick={() => setIsDarkMode(!isDarkMode)}
                  className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 transition-colors"
                  title="สลับธีม"
                >
                  <i className={`fas ${isDarkMode ? 'fa-sun' : 'fa-moon'} text-sm`} />
                </button>
                <button
                  onClick={() => setView(view === 'admin' ? 'chat' : isAuthenticated ? 'admin' : 'admin-login')}
                  className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500 dark:text-slate-400 transition-colors"
                  title="Admin Panel"
                >
                  <i className="fas fa-cog text-sm" />
                </button>
                {isAuthenticated && (
                  <button
                    onClick={logout}
                    className="p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-500 hover:text-red-500 transition-colors ml-auto"
                    title="ออกจากระบบ"
                  >
                    <i className="fas fa-sign-out-alt text-sm" />
                  </button>
                )}
              </div>
            </div>

            {/* ─── Main Chat Area ───────────────────────────────────────────── */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Chat Messages */}
              <div
                id="chat-messages"
                className="flex-1 overflow-y-auto custom-scrollbar px-6 py-6 space-y-4"
              >
                {/* Mascot Welcome (shown when only 1 bot message) */}
                {activeSession?.messages?.length <= 1 && (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <img
                      src={currentMascot}
                      alt="TUH Mascot"
                      className="w-40 h-40 object-contain animate-mascot-float mb-4"
                    />
                    <h2 className="text-3xl font-bold text-tuh-gradient mb-2">TUH Chatbot AI</h2>
                    <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm">
                      เริ่มการสนทนาของคุณโดยพิมพ์คำถามด้านล่าง
                    </p>

                    {/* Predefined FAQs */}
                    {publicSettings?.predefined_faqs?.length > 0 && (
                      <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-lg">
                        {publicSettings.predefined_faqs.map((faq, i) => (
                          <button
                            key={i}
                            onClick={() => sendMessage(faq.question)}
                            className="faq-pill-button text-sm"
                          >
                            {faq.question}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Messages */}
                {activeSession?.messages?.map(msg => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    botAvatar={botAvatar}
                    onFeedback={submitFeedback}
                    isDarkMode={isDarkMode}
                  />
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-full overflow-hidden border-2 border-blue-400/30">
                      <img src={botAvatar} alt="Bot" className="w-full h-full object-cover" />
                    </div>
                    <div className="glass-panel px-4 py-3 rounded-2xl rounded-tl-sm">
                      <div className="flex gap-1.5">
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Bar */}
              <InputBar
                onSend={sendMessage}
                isLoading={isLoading}
                isDarkMode={isDarkMode}
              />
            </div>
          </>
        )}
      </Suspense>
    </div>
  );
}

// ─── Root App with Providers ───────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
