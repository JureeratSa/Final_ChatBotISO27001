/**
 * TUH Chatbot AI — useSidebarResize Custom Hook
 * ควบคุมการลากปรับความกว้างของ Sidebar (แถบเมนูซ้าย):
 * 1. รองรับการทำงานทั้งผ่าน Mouse Events (Desktop) และ Touch Events (Mobile/Tablet)
 * 2. มีการจำกัดขนาดขอบเขต (Min: 240px, Max: 480px หรือ 85% ของความกว้างหน้าจอ)
 * 3. บันทึกความกว้างล่าสุดลงใน localStorage ('tuh_sidebar_width')
 */
import { useState, useRef, useEffect } from 'react';

export function useSidebarResize() {
  // โหลดความกว้าง sidebar ที่เคยบันทึกไว้ (ค่า default: 320px)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('tuh_sidebar_width');
    return saved ? parseInt(saved, 10) : 320;
  });

  // ใช้ ref เพื่อตรวจสอบสถานะว่าขณะนี้กำลังลากเมนูอยู่หรือไม่
  const isResizing = useRef(false);

  // เริ่มต้นการลากด้วยเมาส์ (Mouse Event)
  const startResizing = (e) => {
    e.preventDefault();
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none'; // ป้องกันการไฮไลต์ข้อความขณะลาก
  };

  // เริ่มต้นการลากด้วยการสัมผัส (Touch Event)
  const startTouchResizing = (e) => {
    isResizing.current = true;
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    // คำนวณความกว้างใหม่เมื่อขยับเมาส์
    const handleMouseMove = (e) => {
      if (!isResizing.current) return;
      let newWidth = e.clientX;
      const minWidth = 240;
      const maxWidth = Math.min(480, window.innerWidth * 0.85);
      if (newWidth < minWidth) newWidth = minWidth;
      if (newWidth > maxWidth) newWidth = maxWidth;
      setSidebarWidth(newWidth);
    };

    // คำนวณความกว้างใหม่เมื่อเลื่อนนิ้วสัมผัส
    const handleTouchMove = (e) => {
      if (!isResizing.current) return;
      if (e.touches && e.touches[0]) {
        let newWidth = e.touches[0].clientX;
        const minWidth = 240;
        const maxWidth = Math.min(480, window.innerWidth * 0.85);
        if (newWidth < minWidth) newWidth = minWidth;
        if (newWidth > maxWidth) newWidth = maxWidth;
        setSidebarWidth(newWidth);
      }
    };

    // สิ้นสุดการลากด้วยเมาส์และบันทึกค่าลง localStorage
    const handleMouseUp = () => {
      if (isResizing.current) {
        isResizing.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        localStorage.setItem('tuh_sidebar_width', sidebarWidth);
      }
    };

    // สิ้นสุดการลากด้วยนิ้วสัมผัสและบันทึกค่าลง localStorage
    const handleTouchEnd = () => {
      if (isResizing.current) {
        isResizing.current = false;
        document.body.style.userSelect = '';
        localStorage.setItem('tuh_sidebar_width', sidebarWidth);
      }
    };

    // ผูก Event Listeners เข้ากับ document
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd);

    // Cleanup Event Listeners เมื่อ component unmount หรือ sidebarWidth เปลี่ยน
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [sidebarWidth]);

  return { sidebarWidth, startResizing, startTouchResizing };
}

