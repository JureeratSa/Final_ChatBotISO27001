/**
 * TUH Chatbot AI — UserWeb Formatting Utilities
 * ฟังก์ชันช่วยเหลือสำหรับการจัดรูปแบบข้อความและวันที่:
 * 1. stripHtml: ลบแท็ก HTML ออกจากข้อความเพื่อแสดงเป็น Plain text ปลอดภัย
 * 2. formatAnnDate: แปลงวันที่ ISO string เป็นรูปแบบภาษาไทย (พ.ศ. พร้อมเวลา น.)
 */

/**
 * ลบ HTML tags ออกจากข้อความ (ใช้สำหรับทำความสะอาดเนื้อหาประกาศก่อนแสดงผล)
 * @param {string} html - ข้อความ HTML
 * @returns {string} ข้อความแบบ plain text
 */
export const stripHtml = (html) => {
  if (!html) return '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || "";
};

/**
 * แปลงวันที่ ISO (เช่น 2026-09-24T10:30:00) ให้เป็นรูปแบบวันที่ไทย (เช่น 24 ก.ย. 2569 เวลา 10:30 น.)
 * @param {string} dateStr - วันที่รูปแบบ ISO หรือสตริง
 * @returns {string} วันที่รูปแบบภาษาไทย
 */
export const formatAnnDate = (dateStr) => {
  if (!dateStr) return "";
  try {
    const cleanStr = dateStr.replace('T', ' ');
    const parts = cleanStr.split(' ');
    const dateParts = parts[0].split('-');
    if (dateParts.length !== 3) return dateStr;
    const year = parseInt(dateParts[0]);
    const month = parseInt(dateParts[1]);
    const day = parseInt(dateParts[2]);
    const time = parts[1] ? parts[1].substring(0, 5) : "";

    // รายชื่อเดือนย่อภาษาไทย
    const monthNames = [
      "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
      "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
    ];

    // แปลง ค.ศ. เป็น พ.ศ. (+543)
    const thaiYear = year + 543;
    const formattedDate = `${day} ${monthNames[month - 1]} ${thaiYear}`;
    return time ? `${formattedDate} เวลา ${time} น.` : formattedDate;
  } catch (e) {
    return dateStr;
  }
};
