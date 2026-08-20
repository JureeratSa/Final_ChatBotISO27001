import React from 'react';

export const DislikeModal = ({
  showDislikeModal,
  setShowDislikeModal,
  dislikeQuestion,
  dislikeAnswer,
  dislikeReason,
  setDislikeReason,
  dislikeSuccess,
  handleDislikeSubmit
}) => {
  if (!showDislikeModal) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
        {/* ส่วนหัวข้อเสนอแนะที่ไม่พึงพอใจ */}
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-face-frown text-red-500"></i>
            ระบุเหตุผลที่ไม่พึงพอใจ
          </h3>
          <button
            onClick={() => setShowDislikeModal(false)}
            className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        {/* เนื้อหาข้อเสนอแนะที่ไม่พึงพอใจ */}
        {dislikeSuccess ? (
          <div className="p-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-500 text-3xl flex items-center justify-center mx-auto animate-bounce">
              <i className="fa-solid fa-circle-check"></i>
            </div>
            <h4 className="text-lg font-bold text-tuh-navy dark:text-white">ขอบคุณสำหรับข้อมูล!</h4>
            <p className="text-sm text-tuh-indigo/60 dark:text-tuh-pink/60">
              เราจะนำข้อมูลนี้ไปปรับปรุงความถูกต้องของคำตอบให้ดียิ่งขึ้นครับ
            </p>
          </div>
        ) : (
          <form onSubmit={handleDislikeSubmit} className="p-6 space-y-4">
            {/* คำถาม (ปิด) */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คำถามของคุณ</label>
              <div className="p-3.5 bg-slate-50 dark:bg-tuh-navy/30 border border-slate-200 dark:border-tuh-purple/10 rounded-2xl text-sm font-semibold text-slate-700 dark:text-slate-200 select-none max-h-24 overflow-y-auto">
                {dislikeQuestion}
              </div>
            </div>

            {/* คำตอบ (ปิด) */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คำตอบจากบอท</label>
              <div className="p-3.5 bg-slate-50 dark:bg-tuh-navy/30 border border-slate-200 dark:border-tuh-purple/10 rounded-2xl text-sm text-slate-500 dark:text-slate-400 select-none max-h-36 overflow-y-auto whitespace-pre-wrap">
                {dislikeAnswer}
              </div>
            </div>

            {/* ช่องกรอกเหตุผลหรือข้อแก้ไขที่ถูกต้อง */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">ระบุเหตุผลหรือข้อแก้ไขที่ถูกต้อง <span className="text-red-500">*</span></label>
              <textarea
                rows="3"
                required
                value={dislikeReason}
                onChange={(e) => setDislikeReason(e.target.value)}
                placeholder="เช่น ข้อมูลคลาดเคลื่อน, ต้องการรายละเอียดเพิ่ม, คำตอบไม่ชัดเจน..."
                className="w-full p-3.5 rounded-2xl bg-slate-50 dark:bg-tuh-navy/55 border border-slate-200 dark:border-tuh-purple/30 text-sm focus:outline-none focus:ring-2 focus:ring-tuh-rose text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-tuh-pink/40 resize-none font-medium"
              ></textarea>
            </div>

            {/* ปุ่มส่งข้อเสนอแนะที่ไม่พึงพอใจและยกเลิก */}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDislikeModal(false)}
                className="px-4 py-2.5 rounded-xl border border-slate-250 dark:border-tuh-purple/40 text-tuh-indigo/70 dark:text-tuh-pink/70 hover:bg-slate-100 dark:hover:bg-tuh-indigo/60 font-semibold text-sm transition"
              >
                ยกเลิก
              </button>
              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-500 to-rose-600 hover:opacity-90 text-white font-semibold text-sm transition shadow-md shadow-red-500/15"
              >
                ส่งคำอธิบาย
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default DislikeModal;
