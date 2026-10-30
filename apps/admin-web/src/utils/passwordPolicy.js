/**
 * กฎรหัสผ่านแอดมิน — สำเนาของ services/api/app/services/password_policy.py ไว้แสดงเช็กลิสต์ระหว่างพิมพ์
 * ตัวที่บังคับจริงคือ backend (ปฏิเสธรหัสที่ไม่ผ่านเสมอ) แก้กฎต้องแก้ทั้งสองไฟล์
 */
export const MIN_PASSWORD_LENGTH = 8;
export const RECOMMENDED_PASSWORD_LENGTH = 12;

const WEAK_PATTERNS = [
  'password', 'passw', 'qwerty', 'asdfgh', 'zxcvbn', 'admin', 'letmein', 'welcome',
  'iloveyou', '123456', '654321', 'abcdef', '111111', '000000',
];
const LEET = { '@': 'a', '4': 'a', '0': 'o', '1': 'i', '!': 'i', '3': 'e', '$': 's', '5': 's', '7': 't' };

const isWeak = (password, username) => {
  const lowered = password.toLowerCase();
  const normalized = [...lowered].map(c => LEET[c] || c).join('');
  if (WEAK_PATTERNS.some(w => lowered.includes(w) || normalized.includes(w))) return true;
  if (/(.)\1{3,}/.test(lowered)) return true;
  return Boolean(username && username.length >= 3 && lowered.includes(username.toLowerCase()));
};

/** เช็กลิสต์สำหรับแสดงผล — ok=true คือผ่านข้อนั้น */
export const passwordChecks = (password = '', username = '') => [
  { label: `ยาวอย่างน้อย ${MIN_PASSWORD_LENGTH} ตัวอักษร (แนะนำ ${RECOMMENDED_PASSWORD_LENGTH} ตัวขึ้นไป)`, ok: password.length >= MIN_PASSWORD_LENGTH },
  { label: 'มีตัวพิมพ์ใหญ่ (A-Z)', ok: /[A-Z]/.test(password) },
  { label: 'มีตัวพิมพ์เล็ก (a-z)', ok: /[a-z]/.test(password) },
  { label: 'มีตัวเลข (0-9)', ok: /[0-9]/.test(password) },
  { label: 'มีสัญลักษณ์ เช่น ! @ # $ %', ok: /[^A-Za-z0-9]/.test(password) },
  { label: 'ไม่ใช่รหัสเดาง่าย (เช่น 123456, password, admin, qwerty) และไม่มีชื่อผู้ใช้', ok: password.length > 0 && !isWeak(password, username) },
];

export const isPasswordValid = (password, username) => passwordChecks(password, username).every(c => c.ok);
