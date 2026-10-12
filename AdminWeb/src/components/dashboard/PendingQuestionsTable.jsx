/**
 * PendingQuestionsTable — ตารางคำถามที่บอทตอบไม่ได้ล่าสุด (สูงสุด 5 รายการ) ในหน้า Dashboard
 * กดปุ่ม "เพิ่มใน FAQs" เพื่อเปิด AnswerFaqModal แยกออกมาจาก DashboardPage.jsx เดิม
 */
export default function PendingQuestionsTable({ items, onAnswerClick }) {
  return (
    <div className="lg:col-span-2 tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
          <div>
            <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
              <i className="fa-solid fa-clipboard-list text-tuh-pink"></i> คำถามที่บอทงงล่าสุด (Action Needed)
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">แอดมินสามารถกดเพื่อตอบคำถามและเพิ่มเข้าระบบ FAQs ได้ทันที</p>
          </div>
          <span className="px-2.5 py-1 text-xs font-black rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
            {items.length} รายการล่าสุด
          </span>
        </div>

        {items.length === 0 ? (
          <div className="py-12 text-center text-slate-400 dark:text-slate-500 font-bold space-y-2">
            <div className="text-4xl"><i className="fa-regular fa-face-laugh-beam"></i></div>
            <p>ยอดเยี่ยม! ไม่มีคำถามที่บอทตอบไม่ได้ค้างอยู่เลย</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-tuh-purple/10 text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-3 pl-2">ข้อความคำถามจากผู้ใช้</th>
                  <th className="pb-3 text-center">ถามซ้ำ</th>
                  <th className="pb-3">วันที่ถาม</th>
                  <th className="pb-3 text-right">การจัดการ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/5 font-semibold text-tuh-navy dark:text-slate-100">
                {items.map((u, idx) => (
                  <tr key={u.id || idx} className="hover:bg-slate-50/50 dark:hover:bg-tuh-purple/5 transition-all">
                    <td className="py-3.5 pl-2 font-bold max-w-xs truncate pr-4">{u.query}</td>
                    <td className="py-3.5 text-center">
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-tuh-purple/20 text-slate-600 dark:text-slate-300 font-black">
                        {u.count}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-400 dark:text-slate-400 font-bold">
                      {new Date(u.timestamp).toLocaleDateString('th-TH', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </td>
                    <td className="py-3.5 text-right pr-2">
                      <button
                        onClick={() => onAnswerClick(u)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-tuh-pink/15 hover:bg-tuh-pink/25 text-tuh-rose text-xs font-black transition active:scale-[0.97]"
                      >
                        <i className="fa-solid fa-plus-circle"></i> เพิ่มใน FAQs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
