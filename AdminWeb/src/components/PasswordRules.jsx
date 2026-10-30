import { passwordChecks, RECOMMENDED_PASSWORD_LENGTH } from '../utils/passwordPolicy';

/**
 * PasswordRules — เช็กลิสต์กฎรหัสผ่านที่อัปเดตตามที่พิมพ์ (ข้อที่ผ่านเป็นสีเขียว)
 * ใช้ในหน้าโปรไฟล์ (เปลี่ยนรหัสตัวเอง) และฟอร์มสร้าง/แก้บัญชีแอดมิน
 */
export default function PasswordRules({ password = '', username = '' }) {
  const checks = passwordChecks(password, username);
  return (
    <div className="rounded-2xl bg-slate-50 dark:bg-black/20 border border-slate-200/70 dark:border-tuh-purple/20 p-3.5 space-y-1.5">
      <p className="text-xs font-extrabold text-slate-600 dark:text-slate-300">เงื่อนไขรหัสผ่าน (ต้องผ่านทุกข้อ)</p>
      {checks.map(c => (
        <div key={c.label} className={`flex items-start gap-2 text-xs font-semibold ${c.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`}>
          <i className={`fa-solid ${c.ok ? 'fa-circle-check' : 'fa-circle'} mt-0.5 text-[11px]`}></i>
          <span>{c.label}</span>
        </div>
      ))}
      {password.length >= 8 && password.length < RECOMMENDED_PASSWORD_LENGTH && (
        <p className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 pt-1">
          <i className="fa-solid fa-lightbulb mr-1"></i>ใช้ได้แล้ว แต่ถ้ายาว {RECOMMENDED_PASSWORD_LENGTH} ตัวขึ้นไปจะปลอดภัยกว่า
        </p>
      )}
    </div>
  );
}
