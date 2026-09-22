import { useState } from 'react';

// เปิด/ปิดแถบด้านข้าง + สถานะ "คัดลอกสำเร็จ" ของข้อความ (พร้อม timeout ล้างสถานะ)
export function useSidebarToggle() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 768);
  const [copiedId, setCopiedId] = useState(null);

  const handleCopyMessage = (text, msgId) => {
    let cleanedText = text;
    cleanedText = cleanedText.replace(/\*\*(.*?)\*\*/g, '$1');
    cleanedText = cleanedText.replace(/\[(.*?)\]\((.*?)\)/g, '$1 ($2)');

    navigator.clipboard.writeText(cleanedText).then(() => {
      setCopiedId(msgId);
      setTimeout(() => {
        setCopiedId(null);
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
    });
  };

  return { isSidebarOpen, setIsSidebarOpen, copiedId, handleCopyMessage };
}
