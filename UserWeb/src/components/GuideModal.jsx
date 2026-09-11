import React from 'react';

export const GuideModal = ({ showGuide, setShowGuide, parseMarkdown }) => {
  if (!showGuide) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
        {/* ส่วนหัวของคู่มือการใช้งาน */}
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 bg-slate-50 dark:bg-tuh-navy/35">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-circle-info text-tuh-rose"></i>
            คู่มือการใช้งานระบบแชทบอท
          </h3>
        </div>

        {/* เนื้อหาคู่มือการใช้งาน */}
        <div className="p-6 overflow-y-auto custom-scrollbar">
          <video
            src="/user-guide.mp4"
            controls
            className="w-full rounded-xl border border-slate-200 dark:border-tuh-purple/30"
          >
            เบราว์เซอร์ของคุณไม่รองรับการเล่นวิดีโอ
          </video>
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
  );
};

export default GuideModal;
