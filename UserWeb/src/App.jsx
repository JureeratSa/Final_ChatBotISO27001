import React, { useState } from 'react';
import logo from './logo.png';
import { Sidebar } from './components/Sidebar';
import { MessageBubble } from './components/MessageBubble';
import { InputBar } from './components/InputBar';
import { GuideModal } from './components/GuideModal';
import { FeedbackModal } from './components/FeedbackModal';
import { DislikeModal } from './components/DislikeModal';
import { AnnouncementModal } from './components/AnnouncementModal';
import { stripHtml, formatAnnDate } from './utils/formatters';
import { API_URL, parseMarkdown } from './utils/chatUtils';
import { useClock } from './hooks/useClock';
import { useTheme } from './hooks/useTheme';
import { useSidebarResize } from './hooks/useSidebarResize';
import { useFontSize } from './hooks/useFontSize';
import { useSidebarToggle } from './hooks/useSidebarToggle';
import { useChatSessions } from './hooks/useChatSessions';
import { useWelcomeSettings } from './hooks/useWelcomeSettings';
import { useFaqVisibility } from './hooks/useFaqVisibility';
import { useChatInput } from './hooks/useChatInput';
import { useFeedbackModal } from './hooks/useFeedbackModal';
import { useDislikeModal } from './hooks/useDislikeModal';
import { useAnnouncements } from './hooks/useAnnouncements';
import { useUserIp } from './hooks/useUserIp';

function App() {
  const currentTime = useClock();
  const { isDarkMode, setIsDarkMode, currentMascot, currentBotAvatar } = useTheme();
  const { sidebarWidth, startResizing, startTouchResizing } = useSidebarResize();
  const { fontSize, setFontSize } = useFontSize();
  const { isSidebarOpen, setIsSidebarOpen, copiedId, handleCopyMessage } = useSidebarToggle();

  // showGuide เป็นสถานะเล็กๆ ที่ไม่มี effect ผูกอยู่ จึงเก็บไว้ตรงนี้แทนที่จะแยกเป็น hook
  const [showGuide, setShowGuide] = useState(false);

  const {
    sessions, setSessions, activeSessionId, setActiveSessionId,
    activeSession, isActiveSessionLatest,
    handleNewChat: handleNewChatWithGreeting, handleDeleteSession
  } = useChatSessions({ currentTime, setIsSidebarOpen });

  // useWelcomeSettings ต้องถูกเรียกหลัง useChatSessions เพราะต้องพึ่ง setSessions จากที่นั่น (มัน patch
  // ข้อความต้อนรับ/คำทักทายลงใน session ที่ยังเป็นข้อความเริ่มต้นอยู่ ผ่าน fetch ตอน mount)
  const { welcomeMessage, chatGreeting, faqsList } = useWelcomeSettings({ setSessions });

  // handleNewChat ของ useChatSessions รับ chatGreeting ปัจจุบันเป็นพารามิเตอร์ (แทนการปิด closure ค่า
  // จาก useWelcomeSettings ตรงๆ ซึ่งเรียกทีหลังในลำดับ hook ของ App.jsx)
  const handleNewChat = () => handleNewChatWithGreeting(chatGreeting);

  const { showFaqs, setShowFaqs } = useFaqVisibility({ sessions, activeSessionId });

  const {
    showFeedback, setShowFeedback,
    feedbackRating, setFeedbackRating,
    feedbackText, setFeedbackText,
    feedbackSuccess, feedbackError,
    isForcedFeedback, setIsForcedFeedback,
    handleFeedbackSubmit
  } = useFeedbackModal();

  const {
    showDislikeModal, setShowDislikeModal,
    dislikeQuestion, dislikeAnswer,
    dislikeReason, setDislikeReason,
    dislikeSuccess, dislikeError,
    handleDislikeSubmit, openDislikeModal
  } = useDislikeModal();

  const { activeAnnouncements, showAnnModal, handleCloseAnnModal } = useAnnouncements();
  const userIp = useUserIp();

  const {
    inputValue, setInputValue, isTyping,
    inputRef, chatEndRef, chatContainerRef,
    handleSendMessage, handleStopGeneration
  } = useChatInput({
    sessions, activeSessionId, setSessions, activeSession, faqsList,
    setShowFaqs, setIsForcedFeedback, setShowFeedback
  });

  // ให้คะแนนถูกใจ/ไม่ถูกใจข้อความของบอท — ประกอบข้อมูลจากทั้ง useChatSessions (sessions/setSessions)
  // และ useDislikeModal (openDislikeModal) จึงคงไว้ตรงนี้ใน App.jsx แทนที่จะยัดใส่ hook ใดหนึ่งเดียว
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
          openDislikeModal({ question: userQuery, answer: msgText, msgId });
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
                      isDarkMode={isDarkMode}
                      copiedId={copiedId}
                      isTyping={isTyping}
                      currentBotAvatar={currentBotAvatar}
                      handleLikeMessage={handleLikeMessage}
                      handleCopyMessage={handleCopyMessage}
                      setInputValue={setInputValue}
                      parseMarkdown={parseMarkdown}
                      apiUrl={API_URL}
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
          feedbackError={feedbackError}
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
          dislikeError={dislikeError}
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
