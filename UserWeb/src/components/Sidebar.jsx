import React from 'react';

export const Sidebar = ({
  isSidebarOpen,
  setIsSidebarOpen,
  isDarkMode,
  setIsDarkMode,
  sidebarWidth,
  fontSize,
  setFontSize,
  sessions,
  activeSessionId,
  setActiveSessionId,
  currentTime,
  handleNewChat,
  handleDeleteSession,
  setShowGuide,
  setShowFeedback,
  setIsForcedFeedback,
  startResizing,
  startTouchResizing,
  logo
}) => {
  return (
    <>
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
                className={`flex-1 text-center text-xs py-2 px-1 rounded-md font-semibold transition ${fontSize === 'normal' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
              >
                ปกติ
              </button>
              <button
                onClick={() => setFontSize('large')}
                className={`flex-1 text-center text-xs py-2 px-1 rounded-md font-semibold transition ${fontSize === 'large' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
              >
                ใหญ่
              </button>
              <button
                onClick={() => setFontSize('xl')}
                className={`flex-1 text-center text-xs py-2 px-1 rounded-md font-semibold transition ${fontSize === 'xl' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-tuh-navy/60 dark:text-slate-300 hover:bg-slate-300/30 dark:hover:bg-white/5'}`}
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
            className="hidden md:block absolute top-0 right-0 bottom-0 w-3 -mr-1.5 cursor-col-resize z-50 group"
            title="ลากเพื่อปรับขนาดเมนู"
          >
            <div className="w-1 h-full mx-auto bg-transparent group-hover:bg-tuh-rose/40 dark:group-hover:bg-tuh-purple/40 transition-colors duration-150" />
          </div>
        )}
      </aside>
    </>
  );
};

export default Sidebar;
