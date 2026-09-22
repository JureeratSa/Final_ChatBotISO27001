// TUH Chatbot AI — UserWeb formatting utilities
// แยกออกมาจาก App.jsx เพื่อ unit test ได้ด้วย Vitest โดยไม่ต้อง render component เต็มรูปแบบ
// (ดู web_testing/unit-frontend/formatters.test.js) — logic และพฤติกรรมเดิมทุกกรณี ไม่ได้แก้ไข

export const stripHtml = (html) => {
  if (!html) return '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || "";
};

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

    const monthNames = [
      "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
      "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
    ];

    const thaiYear = year + 543;
    const formattedDate = `${day} ${monthNames[month - 1]} ${thaiYear}`;
    return time ? `${formattedDate} เวลา ${time} น.` : formattedDate;
  } catch (e) {
    return dateStr;
  }
};
