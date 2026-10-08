/**
 * CsatDoughnutChart — โดนัทชาร์ต SVG แสดงสัดส่วนความพึงพอใจ (like vs dislike) ในหน้า Dashboard
 * แยกออกมาจาก DashboardPage.jsx เดิม
 *
 * นับเฉพาะคำตอบที่มีคนกด like/dislike จริงเท่านั้น (ไม่รวมคำถามที่ไม่มีใครกด feedback เลย
 * เพื่อให้ตรงกับตัวเลข CSAT กลางวงและ subtitle ของการ์ด)
 */
export default function CsatDoughnutChart({ stats }) {
  const likeVal = stats.likes || 0;
  const dislikeVal = stats.dislikes || 0;
  const doughnutTotal = likeVal + dislikeVal;
  const likePct = doughnutTotal > 0 ? Math.round((likeVal / doughnutTotal) * 100) : 0;
  const dislikePct = doughnutTotal > 0 ? 100 - likePct : 0;

  return (
    <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
      <div className="border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
        <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
          <i className="fa-solid fa-face-smile text-tuh-pink"></i> สัดส่วนความพึงพอใจ CSAT
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">แบ่งตามการกดยอมรับคำตอบของผู้ใช้งานแชทบอท</p>
      </div>

      <div className="flex-1 flex items-center justify-center gap-6">
        {/* SVG Doughnut */}
        <div className="relative w-32 h-32 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
            {/* Segment 1: Good (Green) */}
            <circle
              cx="18"
              cy="18"
              r="15.915"
              fill="transparent"
              stroke="#10b981"
              strokeWidth="3.2"
              strokeDasharray={`${likePct} ${100 - likePct}`}
              strokeDashoffset="0"
            />
            {/* Segment 2: Needs Improvement (Red) */}
            <circle
              cx="18"
              cy="18"
              r="15.915"
              fill="transparent"
              stroke="#ef4444"
              strokeWidth="3.2"
              strokeDasharray={`${dislikePct} ${100 - dislikePct}`}
              strokeDashoffset={`-${likePct}`}
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className="text-xs font-black text-slate-400 uppercase tracking-widest">CSAT</span>
            <span className="text-xl font-black text-emerald-500 dark:text-emerald-400">
              {likePct}%
            </span>
          </div>
        </div>

        {/* Legend details */}
        <div className="space-y-2 text-xs font-bold text-slate-600 dark:text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>ดีมาก: {likePct}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
            <span>ปรับปรุง: {dislikePct}%</span>
          </div>
          <div className="text-[11px] font-medium text-slate-400 dark:text-slate-500 pt-1">
            จาก {doughnutTotal} คำตอบที่มีคนกด feedback
          </div>
        </div>
      </div>
    </div>
  );
}
