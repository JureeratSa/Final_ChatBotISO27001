import { useAdminContext } from '../context/AdminContext';

/**
 * FaqsPage — แท็บ "คู่มือตอบกลับ (FAQs)" รายการคำถามด่วน 6 ปุ่มหน้าแรก/ห้องแชท พร้อม
 * modal แก้ไขข้อความคำถาม/ไอคอน/คำตอบ — แยกออกมาจาก App.jsx เดิม
 */
export default function FaqsPage() {
  const {
    handleOpenEditPredefinedFaqModal,
    handleSavePredefinedFaq,
    predefinedFaqAnswer,
    predefinedFaqIcon,
    predefinedFaqQuestion,
    selectedPredefinedFaq,
    setPredefinedFaqAnswer,
    setPredefinedFaqIcon,
    setPredefinedFaqQuestion,
    setSelectedPredefinedFaq,
    setShowEditPredefinedFaqModal,
    settings,
    showEditPredefinedFaqModal,
  } = useAdminContext();

  return (
    <>
      <div className="space-y-6 animate-slide-in">
        {/* Predefined 6 Home FAQs */}
        <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20">
            <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-circle-question text-tuh-rose"></i> คำถามด่วนหน้าแรกและในห้องแชท (แสดง 4 คำถามแรกบนหน้าแรก และทั้งหมดในห้องแชท)</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">คุณสามารถแก้ไขข้อความคำถาม ไอคอน และคำตอบของทั้ง 6 คำถามได้ที่นี่ (โดย 4 คำถามแรกจะนำไปแสดงเป็นปุ่มในหน้าแรกต้อนรับของฝั่งผู้ใช้ และทั้งหมดจะแสดงในปุ่มตัวเลือกคำถามที่พบบ่อยในห้องแชท)</p>
          </div>

          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            {(!settings.predefined_faqs || settings.predefined_faqs.length === 0) ? (
              <div className="col-span-2 p-10 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-3xl">
                กำลังโหลดหรือไม่มีรายการคำถามที่พบบ่อย...
              </div>
            ) : (
              settings.predefined_faqs.map(faq => (
                <div key={faq.id} className="p-4 tuh-glass-2 rounded-2xl flex justify-between items-center hover:border-tuh-rose/30 transition shadow-sm">
                  <div className="space-y-1.5 max-w-[85%]">
                    <h4 className="font-extrabold text-slate-800 dark:text-white flex items-center gap-2 text-[14px]">
                      <span className="w-6 h-6 rounded-lg bg-tuh-pink text-tuh-rose flex items-center justify-center text-xs shrink-0 font-black">
                        <i className={`fa-solid ${faq.icon || 'fa-circle-question'}`}></i>
                      </span>
                      <span className="truncate" title={faq.question}>{faq.question}</span>
                    </h4>
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-350 pl-8 line-clamp-2 leading-relaxed">
                      {faq.answer || faq.response || <span className="italic text-slate-400 font-medium">(ค้นหาคำตอบอัตโนมัติจากไฟล์ PDF)</span>}
                    </p>
                  </div>
                  <button
                    onClick={() => handleOpenEditPredefinedFaqModal(faq)}
                    className="p-2.5 text-tuh-rose hover:bg-tuh-rose/10 rounded-xl transition flex items-center justify-center shrink-0"
                    title="แก้ไขปุ่ม FAQ นี้"
                  >
                    <i className="fa-solid fa-pen-to-square text-base"></i>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* MODAL: EDIT PREDEFINED FAQ MODAL */}
      {showEditPredefinedFaqModal && selectedPredefinedFaq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-pen-to-square text-tuh-rose"></i> แก้ไขคำถามที่พบบ่อย (ปุ่มหน้าแรก)
              </h3>
              <button
                onClick={() => { setShowEditPredefinedFaqModal(false); setSelectedPredefinedFaq(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSavePredefinedFaq} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">หัวข้อคำถาม (ปุ่ม)</label>
                <input
                  type="text"
                  required
                  placeholder="พิมพ์ประโยคคำถาม..."
                  value={predefinedFaqQuestion}
                  onChange={(e) => setPredefinedFaqQuestion(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  คลาสไอคอน FontAwesome (เช่น fa-circle-question, fa-eye, fa-hospital)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-tuh-rose flex items-center justify-center">
                    <i className={`fa-solid ${predefinedFaqIcon || 'fa-circle-question'}`}></i>
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="ใส่คลาสไอคอน FontAwesome..."
                    value={predefinedFaqIcon}
                    onChange={(e) => setPredefinedFaqIcon(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-3 pl-10 pr-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  คำตอบของคำถามนี้ (หากต้องการระบุคำตอบตายตัว)
                </label>
                <textarea
                  placeholder="พิมพ์ข้อความคำตอบของปุ่มนี้หากต้องการคำตอบที่แน่นอน... (หรือเว้นว่างไว้เพื่อให้ AI ค้นหาจาก PDF)"
                  value={predefinedFaqAnswer}
                  onChange={(e) => setPredefinedFaqAnswer(e.target.value)}
                  rows={4}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm whitespace-pre-wrap leading-relaxed"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowEditPredefinedFaqModal(false); setSelectedPredefinedFaq(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-floppy-disk mr-1.5"></i> บันทึกข้อมูล
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
