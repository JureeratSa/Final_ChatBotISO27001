import React from 'react';

export const FeedbackModal = ({
  showFeedback,
  setShowFeedback,
  feedbackRating,
  setFeedbackRating,
  feedbackText,
  setFeedbackText,
  feedbackSuccess,
  isForcedFeedback,
  handleFeedbackSubmit
}) => {
  if (!showFeedback) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
        {/* ส่วนหัวข้อเสนอแนะ */}
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-comments text-tuh-rose"></i>
            ส่งข้อเสนอแนะการใช้งาน
          </h3>
          {!isForcedFeedback && (
            <button
              onClick={() => setShowFeedback(false)}
              className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
            >
              <i className="fa-solid fa-xmark"></i>
            </button>
          )}
        </div>

        {/* เนื้อหาข้อเสนอแนะ */}
        {feedbackSuccess ? (
          <div className="p-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/30 text-emerald-500 text-3xl flex items-center justify-center mx-auto animate-bounce">
              <i className="fa-solid fa-circle-check"></i>
            </div>
            <h4 className="text-lg font-bold text-tuh-navy dark:text-white">ส่งข้อเสนอแนะเรียบร้อย!</h4>
            <p className="text-sm text-tuh-indigo/60 dark:text-tuh-pink/60">
              ขอบคุณสำหรับคำติชมและข้อแนะนำ งานสารสนเทศโรงพยาบาลธรรมศาสตร์ฯ จะนำไปพัฒนาแชทบอทให้ดียิ่งขึ้นครับ
            </p>
          </div>
        ) : (
          <form onSubmit={handleFeedbackSubmit} className="p-6 space-y-4">

            {/* แถบดาวแสดงความพึงพอใจ */}
            <div>
              <label className="block text-xs font-semibold text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">คะแนนความพึงพอใจการใช้ระบบ</label>
              <div className="flex gap-2 items-center">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    type="button"
                    key={star}
                    onClick={() => setFeedbackRating(star)}
                    className="text-2xl transition hover:scale-110 focus:outline-none"
                  >
                    <i className={`fa-solid fa-star ${star <= feedbackRating ? 'text-amber-400' : 'text-slate-200 dark:text-white'}`}></i>
                  </button>
                ))}
                <span className="text-xs text-tuh-indigo/40 dark:text-tuh-pink/40 font-bold ml-2">
                  ({feedbackRating} คะแนน)
                </span>
              </div>
            </div>

            {/* ช่องกรอกข้อความ */}
            <div>
              <label className="block text-xs font-semibold text-tuh-indigo/60 dark:text-tuh-pink/60 mb-1.5">ข้อแนะนำ / สิ่งที่ควรปรับปรุง</label>
              <textarea
                rows="3"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="กรอกข้อความแนะนำระบบหรือแจ้งปัญหาไอทีที่พบเพิ่มเติมได้ที่นี่... (ไม่บังคับระบุ)"
                className="w-full p-3 rounded-xl bg-slate-50 dark:bg-tuh-navy/55 border border-slate-200 dark:border-tuh-purple/30 text-sm focus:outline-none focus:ring-2 focus:ring-tuh-rose text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-tuh-pink/40 resize-none"
              ></textarea>
            </div>

            {/* ปุ่มส่งข้อเสนอแนะและยกเลิก */}
            <div className="flex justify-end gap-2 pt-2">
              {!isForcedFeedback && (
                <button
                  type="button"
                  onClick={() => setShowFeedback(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-250 dark:border-tuh-purple/40 text-tuh-indigo/70 dark:text-tuh-pink/70 hover:bg-slate-100 dark:hover:bg-tuh-indigo/60 font-semibold text-sm transition"
                >
                  ยกเลิก
                </button>
              )}
              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-tuh-gradient-2 hover:opacity-90 text-white font-semibold text-sm transition shadow-md shadow-tuh-rose/15"
              >
                {isForcedFeedback ? 'ส่งความเห็นเพื่อปิดแชทบอท' : 'ส่งข้อเสนอแนะ'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default FeedbackModal;
