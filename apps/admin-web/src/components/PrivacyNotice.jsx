import { useState } from 'react';
import { createPortal } from 'react-dom';

/**
 * PrivacyNotice — ไอคอน (i) แจ้งเรื่องการบันทึกการใช้งาน (audit log) ตาม PDPA
 * ต้องแจ้งเจ้าของข้อมูลก่อน/ขณะเก็บ IP, User-Agent, วันเวลา, ผู้ใช้ และกิจกรรม (ดู services/api/app/services/audit_service.py)
 * - variant="login": หน้า Login (ข้อความทั่วไป)
 * - variant="admin": หน้าระบบผู้ดูแล (แจ้งชัดกว่า เพราะแอดมินแก้ข้อมูลและสิทธิ์ได้)
 */

const NOTICES = {
  login: {
    title: 'การบันทึกการใช้งานระบบ',
    body: (
      <>
        <p>
          การเข้าสู่ระบบและการใช้งานระบบนี้จะถูกบันทึกเพื่อวัตถุประสงค์ด้านความมั่นคงปลอดภัย การตรวจสอบการใช้งาน
          และการปฏิบัติตามกฎหมาย โดยระบบอาจเก็บข้อมูล เช่น ชื่อผู้ใช้ วันเวลา ที่อยู่ IP อุปกรณ์/เบราว์เซอร์
          และกิจกรรมการใช้งาน
        </p>
        <p className="mt-3">ข้อมูลจะถูกเก็บรักษาตามนโยบายการเก็บรักษาข้อมูลขององค์กร</p>
      </>
    ),
  },
  admin: {
    title: 'การบันทึกการดำเนินการของผู้ดูแลระบบ',
    body: (
      <>
        <p>
          การเข้าใช้งานและการดำเนินการทั้งหมดในระบบผู้ดูแลจะถูกบันทึกเพื่อการตรวจสอบย้อนหลัง ความมั่นคงปลอดภัย
          และการปฏิบัติตามกฎหมาย รวมถึงข้อมูลผู้ใช้ วันเวลา ที่อยู่ IP อุปกรณ์
          และการเปลี่ยนแปลงข้อมูลหรือสิทธิ์การเข้าถึง
        </p>
      </>
    ),
  },
};

export default function PrivacyNotice({ variant = 'admin', className = '', label }) {
  const [open, setOpen] = useState(false);
  const notice = NOTICES[variant];

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-1.5 transition active:scale-95 ${className}`}
        title={notice.title}
        aria-label={notice.title}
      >
        <i className="fa-solid fa-circle-info"></i>
        {label && <span>{label}</span>}
      </button>

      {/* render ที่ document.body — ปุ่มอยู่ใน header ที่มี backdrop-blur ซึ่งทำให้ position:fixed
          ยึดกับ header แทนหน้าจอ (modal เลยถูกตัด/ซ้อนกับเนื้อหาด้านล่าง) */}
      {open && createPortal(
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
          onClick={() => setOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            className="w-full max-w-lg bg-white dark:bg-[#1e0533] text-tuh-navy dark:text-slate-100 rounded-3xl shadow-2xl overflow-hidden animate-slide-in text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center">
              <h3 className="font-extrabold text-base flex items-center gap-2">
                <i className="fa-solid fa-shield-halved text-tuh-rose"></i> {notice.title}
              </h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-slate-500 dark:text-slate-400 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
                aria-label="ปิด"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>
            <div className="p-6 text-sm leading-relaxed font-medium">{notice.body}</div>
            <div className="px-6 pb-5 text-right">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2 px-5 rounded-xl text-sm transition active:scale-[0.98]"
              >
                รับทราบ
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
