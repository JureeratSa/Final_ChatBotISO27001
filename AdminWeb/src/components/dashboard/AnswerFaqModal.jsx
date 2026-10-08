/**
 * AnswerFaqModal — modal ลงทะเบียนคำตอบตอบกลับ FAQ เปิดจากปุ่ม "เพิ่มใน FAQs" ของ
 * PendingQuestionsTable ในหน้า Dashboard แยกออกมาจาก DashboardPage.jsx เดิม
 * (คืนค่า null ถ้า show=false เหมือนเงื่อนไข `{showFaqModal && (...)}` เดิม)
 */
export default function AnswerFaqModal({
  show,
  currentUnanswered,
  setCurrentUnanswered,
  faqAnswer,
  setFaqAnswer,
  onClose,
  onSubmit,
}) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
        <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-feather text-tuh-rose"></i> ลงทะเบียนคำตอบตอบกลับ FAQ
          </h3>
          <button
            onClick={onClose}
            className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-6 space-y-4">
          {currentUnanswered.query && (
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามจากผู้ใช้</label>
              <div className="p-4 tuh-glass-2 rounded-2xl font-bold">
                {currentUnanswered.query}
              </div>
            </div>
          )}

          {!currentUnanswered.query && (
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามแอดมินตั้งขึ้น</label>
              <input
                type="text"
                required
                placeholder="พิมพ์ประโยคคำถาม..."
                value={currentUnanswered.query || ''}
                onChange={(e) => setCurrentUnanswered({ ...currentUnanswered, query: e.target.value })}
                className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เขียนคู่มือคำตอบ (บอทจะตอบประโยคนี้ตรงๆ ทันที)</label>
            <textarea
              rows="4"
              required
              placeholder="เขียนคำตอบที่สั้น กระชับ ตรงประเด็นสำหรับคำถามนี้..."
              value={faqAnswer}
              onChange={(e) => setFaqAnswer(e.target.value)}
              className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm leading-relaxed"
            ></textarea>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
            >
              ยกเลิก
            </button>
            <button
              type="submit"
              className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
            >
              <i className="fa-solid fa-save mr-1.5"></i> ลงทะเบียนคำตอบสำเร็จ
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
