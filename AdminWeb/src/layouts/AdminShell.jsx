import { useAdminContext } from '../context/AdminContext';
import dog from '../dog.png';
import botAvatar from '../bot_avatar.jpg';

/**
 * AdminShell — โครง layout หลักหลัง login (sidebar navigation + top bar) ครอบเนื้อหา
 * ของแต่ละแท็บที่ส่งมาทาง children — แยกออกมาจาก App.jsx เดิม
 */
export default function AdminShell({ children }) {
  const {
    activeTab,
    adminUser,
    announcements,
    confirmDelete,
    deleteModalState,
    documents,
    errorMsg,
    handleLogout,
    handleTabClick,
    history,
    isDarkMode,
    isSidebarOpen,
    pendingUnansweredCount,
    setDeleteModalState,
    setIsDarkMode,
    setIsSidebarOpen,
    settings,
    successMsg,
    users,
  } = useAdminContext();

  return (
    <div className="flex h-screen overflow-hidden bg-[#faf7ff] text-tuh-navy dark:bg-[#100220] dark:text-white transition-colors duration-300 font-sans">

      {/* Dynamic Floating Background Elements */}
      <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/5 dark:bg-tuh-purple/10 blur-[100px] pointer-events-none animate-float-slow"></div>
      <div className="absolute bottom-40 left-10 w-96 h-96 rounded-full bg-tuh-coral/5 dark:bg-tuh-rose/5 blur-[120px] pointer-events-none animate-float-slower"></div>

      {/* Notifications */}
      {successMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-emerald-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-check text-lg"></i>
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-red-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-exclamation text-lg"></i>
          {errorMsg}
        </div>
      )}

      {/* Mobile Drawer Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar Panel */}
      <aside className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-slate-200 dark:border-tuh-purple/20 bg-[#f5f0ff] dark:bg-tuh-indigo/90 backdrop-blur-md transition-all duration-300 lg:static lg:translate-x-0 ${isSidebarOpen ? 'w-72 translate-x-0 opacity-100' : 'w-0 -translate-x-full lg:translate-x-0 lg:opacity-0 lg:border-r-0 overflow-hidden'}`}>
        {/* Header */}
        <div className="h-[76px] px-5 border-b border-purple-100 dark:border-tuh-purple/20 flex items-center justify-between gap-3 bg-white dark:bg-tuh-indigo/90">
          <div className="flex items-center gap-3">
            <img
              src={dog}
              alt="TUH Dog Logo"
              className="w-10 h-10 rounded-xl object-cover shadow-md shrink-0 border border-slate-100 dark:border-tuh-purple/20"
            />
            <div>
              <h2
                className="font-extrabold text-tuh-navy dark:text-white leading-tight font-roboto"
                style={{ fontSize: 'calc(1.25rem - 2px)' }}
              >
                TUH Admin Chatbot
              </h2>
              <a
                href="https://hospital.tu.ac.th/th"
                target="_blank"
                rel="noopener noreferrer"
                className="text-tuh-indigo/80 dark:text-slate-200 font-bold block mt-0.5 leading-none transition-colors cursor-pointer font-roboto"
                style={{ fontSize: 'calc(0.8rem - 1px)' }}
              >
                Thammasat University Hospital
              </a>
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

        {/* Menu Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto custom-scrollbar">
          <button
            onClick={() => handleTabClick('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'dashboard' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-chart-line text-sm"></i>
            <span>ภาพรวม</span>
          </button>

          <button
            onClick={() => handleTabClick('satisfaction')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'satisfaction' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-face-smile text-sm"></i>
            <span>สถิติความพึงพอใจ</span>
          </button>

          <button
            onClick={() => handleTabClick('documents')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'documents' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-file-pdf text-sm"></i>
            <span>จัดการเอกสาร PDF</span>
          </button>

          <button
            onClick={() => handleTabClick('announcements')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'announcements' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-bullhorn text-sm"></i>
            <span>สร้างและจัดการประกาศ</span>
          </button>

          <button
            onClick={() => handleTabClick('logs')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'logs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <div className="relative">
              <i className="fa-solid fa-circle-question text-sm"></i>
              {pendingUnansweredCount > 0 && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse"></span>
              )}
            </div>
            <span>คำถามที่บอทตอบไม่ได้</span>
            {pendingUnansweredCount > 0 && (
              <span className="ml-auto bg-red-500 text-white text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                {pendingUnansweredCount}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabClick('history')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'history' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-clock-rotate-left text-sm"></i>
            <span>ประวัติการตอบของบอท</span>
          </button>

          <button
            onClick={() => handleTabClick('faqs')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'faqs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-book text-sm"></i>
            <span>คู่มือตอบกลับ (FAQs)</span>
          </button>


          {adminUser.role === 'System Administrator' && (
            <button
              onClick={() => handleTabClick('users')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'users' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
            >
              <i className="fa-solid fa-users text-sm"></i>
              <span>จัดการบัญชีแอดมิน</span>
            </button>
          )}

          <button
            onClick={() => handleTabClick('profile')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'profile' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-user-gear text-sm"></i>
            <span>โปรไฟล์แอดมิน</span>
          </button>

          {adminUser.role === 'System Administrator' && (
            <button
              onClick={() => handleTabClick('settings')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'settings' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
            >
              <i className="fa-solid fa-sliders text-sm"></i>
              <span>ตั้งค่าระบบ AI</span>
            </button>
          )}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-100 dark:border-tuh-purple/20 space-y-2 bg-slate-50/50 dark:bg-tuh-navy/40">
          {/* Theme Toggle */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all font-semibold"
          >
            <div className="flex items-center gap-2.5">
              <i className={`fa-solid ${isDarkMode ? 'fa-sun text-amber-500 animate-spin-slow' : 'fa-moon text-tuh-rose'} text-base`}></i>
              <span>สลับโหมดสี</span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 dark:bg-white/10 font-bold">
              {isDarkMode ? 'โหมดสว่าง' : 'โหมดมืด'}
            </span>
          </button>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 p-3 rounded-xl hover:bg-red-50 dark:hover:bg-red-500/10 text-red-500 transition font-bold text-left"
          >
            <i className="fa-solid fa-arrow-right-from-bracket"></i>
            <span>ออกจากระบบ</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Navbar */}
        <header className="h-[76px] px-4 md:px-6 border-b border-slate-200 dark:border-tuh-purple/20 bg-white/70 dark:bg-tuh-navy/40 backdrop-blur-md flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2.5 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-tuh-indigo/50 transition active:scale-95 shrink-0 animate-fade-in"
                title="เปิดแถบเมนู"
              >
                <i className="fa-solid fa-bars text-lg"></i>
              </button>
            )}
            <h1 className="text-xl font-black tracking-tight flex items-center gap-2">
              <span className="text-tuh-rose shrink-0">
                {activeTab === 'dashboard' && <i className="fa-solid fa-chart-line"></i>}
                {activeTab === 'satisfaction' && <i className="fa-solid fa-face-smile"></i>}
                {activeTab === 'documents' && <i className="fa-solid fa-file-pdf"></i>}
                {activeTab === 'announcements' && <i className="fa-solid fa-bullhorn"></i>}
                {activeTab === 'logs' && <i className="fa-solid fa-circle-question"></i>}
                {activeTab === 'history' && <i className="fa-solid fa-clock-rotate-left"></i>}
                {activeTab === 'faqs' && <i className="fa-solid fa-book"></i>}
                {activeTab === 'settings' && <i className="fa-solid fa-sliders"></i>}
                {activeTab === 'profile' && <i className="fa-solid fa-user-gear"></i>}
                {activeTab === 'users' && <i className="fa-solid fa-users"></i>}
              </span>
              <span className={`${activeTab === 'dashboard' ? 'text-tuh-gradient-light' : 'text-tuh-gradient'} font-black`}>
                {activeTab === 'dashboard' && 'ภาพรวม'}
                {activeTab === 'satisfaction' && 'สถิติความพึงพอใจ'}
                {activeTab === 'documents' && 'จัดการแฟ้มเอกสาร PDF'}
                {activeTab === 'announcements' && 'สร้างและจัดการประกาศระบบ'}
                {activeTab === 'logs' && 'บันทึกคำถามที่บอทตอบไม่ได้'}
                {activeTab === 'history' && 'ประวัติการตอบของบอท'}
                {activeTab === 'faqs' && 'ทะเบียนคู่มือคำตอบ FAQs'}
                {activeTab === 'settings' && 'การตั้งค่าระบบ AI แชทบอท'}
                {activeTab === 'profile' && 'โปรไฟล์ผู้ดูแลระบบ'}
                {activeTab === 'users' && 'จัดการบัญชีแอดมินระบบ'}
              </span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline-flex items-center gap-2 text-sm font-bold px-4 py-2 rounded-full bg-tuh-pink/30 text-tuh-rose border border-tuh-rose/20 dark:bg-tuh-rose/25 dark:text-white dark:border-none shadow-sm">
              <img src={botAvatar} alt="Avatar" className="w-7 h-7 rounded-full object-cover shadow-sm" />
              {adminUser.name} ({adminUser.role})
            </span>
          </div>
        </header>

        {/* Content Box */}
        <div className="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar z-10">
          {children}
        </div>
      </main>

      {/* MODAL: CUSTOM CONFIRM DELETE MODAL — ใช้ร่วมกันทุกแท็บ (เอกสาร/ประกาศ/ผู้ใช้/แบบฟอร์ม) */}
      {deleteModalState.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md bg-white dark:bg-[#1C1950] rounded-3xl border border-slate-200 dark:border-2 dark:border-[#93ABD9] shadow-2xl overflow-hidden p-6 text-center animate-scale-up">
            <div className="w-16 h-16 rounded-full bg-[#E97D30]/15 dark:bg-[#E7BEF8]/20 text-[#E97D30] dark:text-[#F2619C] text-3xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#E97D30]/10 dark:shadow-[#F2619C]/10">
              <i className="fa-solid fa-triangle-exclamation animate-bounce"></i>
            </div>
            <h3 className="text-xl font-black text-slate-900 dark:text-white mb-2.5">
              {deleteModalState.type === 'document' ? 'ยืนยันการลบเอกสาร' :
                deleteModalState.type === 'announcement' ? 'ยืนยันการลบประกาศ' :
                  deleteModalState.type === 'user' ? 'ยืนยันการลบบัญชีแอดมิน' : 'ยืนยันการลบแบบฟอร์ม'}
            </h3>
            <p className="text-sm font-semibold text-slate-600 dark:text-slate-200 mb-6 leading-relaxed whitespace-pre-line">
              คุณแน่ใจหรือไม่ว่าต้องการลบ <span className="font-extrabold text-[#E97D30] dark:text-[#F2619C]">"{deleteModalState.targetName}"</span>?
              {deleteModalState.type === 'document' && '\nข้อมูลใน Vector Index ของเอกสารนี้จะถูกนำออกทั้งหมด'}
              {deleteModalState.type === 'user' && '\nบัญชีแอดมินนี้จะไม่สามารถใช้งานเข้าสู่ระบบหลังบ้านได้อีกต่อไป'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setDeleteModalState({ show: false, type: null, targetId: null, targetName: null })}
                className="px-6 py-2.5 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-[#93ABD9] dark:hover:opacity-90 dark:text-white font-bold transition active:scale-95 text-sm"
              >
                ยกเลิก
              </button>
              <button
                onClick={confirmDelete}
                className="px-6 py-2.5 rounded-2xl bg-[#E97D30] dark:bg-[#F2619C] hover:opacity-90 text-white font-bold transition active:scale-[0.98] shadow-lg shadow-[#E97D30]/25 dark:shadow-[#F2619C]/25 text-sm"
              >
                ลบ
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
