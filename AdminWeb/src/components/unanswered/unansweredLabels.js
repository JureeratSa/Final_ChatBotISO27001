/**
 * ป้ายภาษาไทยของ field การปิดรายการคำถามที่บอทตอบไม่ได้ — ค่า key ต้องตรงกับ Literal ใน
 * Backend/app/schemas/schemas.py (UnansweredUpdate)
 */
export const RESOLUTION_LABELS = {
  custom_faq: 'สอนคำตอบ (FAQ)',
  document_upload: 'อัปโหลดเอกสารใหม่',
  chunk_hint: 'ผูกคำถามกับเอกสาร',
};

export const IGNORE_REASONS = [
  { value: 'spam', label: 'ข้อความขยะ / พิมพ์ผิด' },
  { value: 'chit_chat', label: 'คำทักทาย / คุยเล่น' },
  { value: 'out_of_scope', label: 'นอกขอบเขตงานของโรงพยาบาล' },
  { value: 'other', label: 'อื่นๆ (ระบุในหมายเหตุ)' },
];

export const IGNORE_REASON_LABELS = Object.fromEntries(IGNORE_REASONS.map(r => [r.value, r.label]));
