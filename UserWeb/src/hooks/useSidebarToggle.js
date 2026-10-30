/**
 * TUH Chatbot AI — useSidebarToggle Custom Hook
 * จัดการการเปิด/ปิด Sidebar และฟังก์ชันคัดลอกข้อความแชท (Copy to Clipboard):
 * 1. กำหนดค่าเริ่มต้นการเปิด Sidebar ตามขนาดหน้าจอ (เปิดอัตโนมัติบนจอ >= 768px)
 * 2. คลีน Markdown syntax (bold **, links []) ก่อนคัดลอกลง Clipboard
 * 3. จัดการสถานะ copiedId เพื่อแสดง Feedback ไอคอนติ๊กถูกชั่วคราว (2 วินาที)
 */
import { useState } from 'react';

export function useSidebarToggle() {
  // เปิด Sidebar เป็นค่าเริ่มต้นเฉพาะจอที่วางเมนูข้างแชทได้ (>= 1024px: notebook, MacBook, iPad แนวนอน)
  // จอเล็กกว่านั้น (มือถือ, iPad แนวตั้ง) เมนูเป็นแผงลอยทับแชท จึงปิดไว้ก่อน
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1024);
  // เก็บ ID ข้อความที่เพิ่งถูกคัดลอก เพื่อแสดงสถานะสำเร็จ (ติ๊กถูก)
  const [copiedId, setCopiedId] = useState(null);

  /**
   * คัดลอกข้อความลง Clipboard พร้อมลบเครื่องหมาย Markdown ให้เหลือเฉพาะข้อความอ่านง่าย
   * @param {string} text - ข้อความต้นฉบับ
   * @param {string} msgId - ID ของข้อความที่คัดลอก
   */
  const handleCopyMessage = (text, msgId) => {
    let cleanedText = text;
    // ลบแท็ก bold **text** -> text
    cleanedText = cleanedText.replace(/\*\*(.*?)\*\*/g, '$1');
    // ลบรูปแบบลิงก์ [label](url) -> label (url)
    cleanedText = cleanedText.replace(/\[(.*?)\]\((.*?)\)/g, '$1 ($2)');

    navigator.clipboard.writeText(cleanedText).then(() => {
      setCopiedId(msgId);
      // คืนสถานะไอคอนคัดลอกเดิมหลังผ่านไป 2 วินาที
      setTimeout(() => {
        setCopiedId(null);
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
    });
  };

  return { isSidebarOpen, setIsSidebarOpen, copiedId, handleCopyMessage };
}

