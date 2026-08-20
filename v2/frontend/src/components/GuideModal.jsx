import React from 'react';

export const GuideModal = ({ showGuide, setShowGuide, parseMarkdown }) => {
  if (!showGuide) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
      <div className="bg-white dark:bg-[#1B2062] rounded-3xl max-w-lg w-full max-h-[85vh] flex flex-col border border-slate-200 dark:border-tuh-purple/30 shadow-2xl overflow-hidden">
        {/* ส่วนหัวของคู่มือการใช้งาน */}
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/25 flex items-center justify-between bg-slate-50 dark:bg-tuh-navy/35">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-circle-info text-tuh-rose"></i>
            คู่มือการใช้งานระบบแชทบอท
          </h3>
          <button
            onClick={() => setShowGuide(false)}
            className="w-8 h-8 rounded-full flex items-center justify-center text-tuh-indigo/50 hover:text-tuh-navy dark:text-tuh-pink/50 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-tuh-indigo/80 transition"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        {/* เนื้อหาคู่มือการใช้งาน */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm leading-relaxed custom-scrollbar text-tuh-navy/80 dark:text-tuh-pink/80">
          <p className="font-medium text-tuh-navy dark:text-white">
            ระบบ TUH Chatbot AI พัฒนาขึ้นโดยงานสารสนเทศโรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ เพื่อช่วยเหลือและตอบคำถามเบื้องต้นแก่ผู้ใช้บริการและบุคลากร
          </p>

          <div className="space-y-3">
            <h4 className="font-bold text-tuh-navy dark:text-white border-l-4 border-tuh-rose pl-2">ความสามารถของระบบ:</h4>
            <ul className="list-disc pl-5 space-y-1">
              <li>สอบถามขั้นตอนรับบริการ เช่น การทำบัตรผู้ป่วยใหม่</li>
              <li>ขอช่องทางติดต่อประสานงาน ฝ่ายสารสนเทศไอที</li>
              <li>สอบถามเวลาทำการ ของคลินิกพิเศษนอกราชการ</li>
              <li>ลิงก์การดาวน์โหลดและแนะนำการใช้งาน TUH Easy App</li>
              <li>คำแนะนำการประเมินและดูแลรักษาสุขภาพดวงตากฎ 20-20-20</li>
            </ul>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-tuh-navy dark:text-white border-l-4 border-tuh-rose pl-2">วิธีใช้งานเบื้องต้น:</h4>
            <ul className="list-decimal pl-5 space-y-1">
              <li>กดเลือกที่แถบ **"คำถามที่พบบ่อย"** เพื่อรับคำตอบในเรื่องนั้นได้ทันที</li>
              <li>พิมพ์ข้อความคำถามเกี่ยวกับสิทธิ์การรักษาพยาบาลหรือเรื่องระบบไอทีลงในช่องแชทเพื่อสอบถามระบบ</li>
              <li>เปิดและสลับสิทธิ์หน้าต่างการแชท รวมถึงสร้าง **"เริ่มบทสนทนาใหม่"** ได้จากแถบด้านซ้าย</li>
              <li>สามารถกดปิด/เปิดโหมดถนอมสายตาสำหรับหน้าจอที่เข้มขึ้นลดการล้าดวงตาได้ตลอดเวลา</li>
            </ul>
          </div>

          <div className="p-3 bg-tuh-pink/10 dark:bg-tuh-purple/10 rounded-2xl border border-tuh-rose/20 dark:border-tuh-rose/30 flex gap-3 text-xs">
            <i className="fa-solid fa-lightbulb text-amber-500 text-lg shrink-0"></i>
            <p>
              **ข้อแนะนำการดูแลดวงตา:** หากดวงตาต้องสัมผัสแสงหน้าจอเป็นเวลานาน แนะนำให้สลับเปิด **โหมดมืด (Dark Mode)** เพื่อให้โทนสีพื้นหลังลดการกระเจิงแสงสีฟ้า ช่วยลดความเหนื่อยล้าของสายตา
            </p>
          </div>
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
