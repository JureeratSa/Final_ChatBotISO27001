/**
 * ActiveAnnouncementsPanel — รายการประกาศระบบที่ Active อยู่ตอนนี้ (สูงสุด 3 รายการ) ในหน้า
 * Dashboard แยกออกมาจาก DashboardPage.jsx เดิม
 */
/**
 * ลบแท็ก HTML ออกจากข้อความเพื่อแสดงผลเป็น Plain text สำหรับการ์ดตัวอย่าง
 */
const stripHtml = (html) => {
  if (!html) return '';
  if (typeof window !== 'undefined' && window.DOMParser) {
    try {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      return doc.body.textContent || '';
    } catch {
      // fallback
    }
  }
  return html.replace(/<[^>]*>/g, '');
};

export default function ActiveAnnouncementsPanel({ activeAnns, onManageClick }) {
  return (
    <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
          <div>
            <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
              <i className="fa-solid fa-bullhorn text-tuh-pink"></i> ประกาศระบบที่ทำงานอยู่
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">ประกาศประชาสัมพันธ์แชทบอทล่าสุด</p>
          </div>
          <span className="px-2.5 py-1 text-xs font-black rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            {activeAnns.length} ทำงานอยู่
          </span>
        </div>

        {activeAnns.length === 0 ? (
          <div className="py-12 text-center text-slate-400 dark:text-slate-500 font-bold space-y-2">
            <div className="text-4xl"><i className="fa-solid fa-volume-xmark"></i></div>
            <p>ไม่มีประกาศระบบที่กำลัง Active ในช่วงเวลานี้</p>
          </div>
        ) : (
          <div className="space-y-4">
            {activeAnns.slice(0, 3).map((ann, idx) => (
              <div
                key={ann.id || idx}
                className="p-4 rounded-2xl bg-slate-50/50 dark:bg-tuh-purple/5 border border-slate-100/50 dark:border-tuh-purple/10 hover:border-tuh-rose/25 transition-all"
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-extrabold text-sm text-tuh-navy dark:text-white truncate">{ann.title}</h4>
                  <span className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-black bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    Active
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{stripHtml(ann.content)}</p>
                <div className="mt-2.5 flex items-center justify-between text-[10px] font-bold text-slate-400 dark:text-slate-500 border-t border-slate-100/60 dark:border-tuh-purple/5 pt-2">
                  <span><i className="fa-regular fa-calendar-days"></i> วันที่เผยแพร่:</span>
                  <span>{new Date(ann.start_date).toLocaleDateString('th-TH', { day: 'numeric', month: 'short' })} - {new Date(ann.end_date).toLocaleDateString('th-TH', { day: 'numeric', month: 'short' })}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={onManageClick}
        className="w-full mt-4 py-2.5 px-4 rounded-xl border border-dashed border-slate-200 dark:border-tuh-purple/20 hover:border-tuh-rose/50 hover:text-tuh-rose text-xs font-black transition-all flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400"
      >
        <i className="fa-solid fa-list"></i> จัดการประกาศทั้งหมด
      </button>
    </div>
  );
}
