import React from 'react';

export const AnnouncementModal = ({
  showAnnModal,
  activeAnnouncements,
  handleCloseAnnModal,
  stripHtml,
  formatAnnDate
}) => {
  if (!showAnnModal || !activeAnnouncements || activeAnnouncements.length === 0) return null;

  return (
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
              className={`p-5 rounded-2xl border space-y-2.5 shadow-sm relative overflow-hidden text-left transition ${ann.pinned ? 'border-emerald-500/20 bg-emerald-500/[0.02] dark:bg-emerald-500/[0.04]' : 'border-slate-100 dark:border-tuh-purple/20 bg-slate-50/70 dark:bg-[#100220]/40'}`}
            >
              {/* Decorative color strip on left side */}
              <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${ann.pinned ? 'bg-gradient-to-b from-emerald-500 to-teal-500' : 'bg-gradient-to-b from-tuh-rose to-tuh-pink'}`}></div>

              <div className="pl-2">
                <h4 className="font-extrabold text-base text-tuh-navy dark:text-white flex items-center gap-2">
                  {ann.pinned && <i className="fa-solid fa-thumbtack text-emerald-500 text-xs rotate-45" title="ประกาศปักหมุด"></i>}
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
  );
};

export default AnnouncementModal;
