import React from 'react';

/**
 * CKEditorWrapper — ห่อ CKEditor 4 (โหลดจาก CDN) ให้ใช้งานแบบ controlled component ใน React
 * ใช้เฉพาะในฟอร์มสร้าง/แก้ไขประกาศ (AnnouncementsPage) — แยกออกมาจาก App.jsx เดิม
 */
export default function CKEditorWrapper({ value, onChange, isDarkMode }) {
  const containerRef = React.useRef(null);
  const editorRef = React.useRef(null);
  const [isLoaded, setIsLoaded] = React.useState(!!window.CKEDITOR);

  React.useEffect(() => {
    if (window.CKEDITOR) {
      setIsLoaded(true);
      return;
    }

    let script = document.querySelector('script[src="https://cdn.ckeditor.com/4.22.1/full/ckeditor.js"]');
    if (!script) {
      script = document.createElement('script');
      script.src = "https://cdn.ckeditor.com/4.22.1/full/ckeditor.js";
      script.async = true;
      document.head.appendChild(script);
    }

    const onLoad = () => setIsLoaded(true);
    script.addEventListener('load', onLoad);
    return () => {
      script.removeEventListener('load', onLoad);
    };
  }, []);

  React.useEffect(() => {
    if (isLoaded && window.CKEDITOR && containerRef.current) {
      window.CKEDITOR.config.language = 'th';
      // เดิม allowedContent = true ปิด Advanced Content Filter ของ CKEditor ทั้งหมด ทำให้แปะ
      // <script>/onerror ผ่าน editor ได้ตรงๆ — ปล่อยให้ CKEditor กรองตาม toolbar ที่อนุญาตแทน
      // (Backend ก็ sanitize อีกชั้นด้วย nh3 ก่อนเก็บ DB เป็น defense-in-depth)
      window.CKEDITOR.config.versionCheck = false; // Disable security warnings

      const editor = window.CKEDITOR.replace(containerRef.current, {
        height: 200,
        versionCheck: false,
        removePlugins: 'elementspath',
        toolbar: [
          { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', '-', 'RemoveFormat'] },
          { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight'] },
          { name: 'links', items: ['Link', 'Unlink'] },
          { name: 'insert', items: ['Table'] }
        ],
        contentsCss: isDarkMode
          ? 'data:text/css,body{background-color:#2c0548 !important;color:#ffffff !important;font-family:sans-serif;padding:10px;}'
          : 'data:text/css,body{background-color:#ffffff !important;color:#0f172a !important;font-family:sans-serif;padding:10px;}'
      });

      editorRef.current = editor;

      // Set initial value
      editor.setData(value || '');

      // Listen to change event
      editor.on('change', () => {
        const data = editor.getData();
        onChange(data);
      });

      return () => {
        if (editor) {
          editor.destroy();
        }
      };
    }
  }, [isLoaded, isDarkMode]);

  React.useEffect(() => {
    if (editorRef.current && editorRef.current.getData() !== value) {
      editorRef.current.setData(value || '');
    }
  }, [value]);

  return (
    <div className="text-black dark:text-black">
      {!isLoaded && <div className="p-4 text-center text-slate-500">กำลังโหลดตัวแก้ไขข้อความ...</div>}
      <textarea ref={containerRef} style={{ display: isLoaded ? 'block' : 'none', visibility: 'hidden' }} />
    </div>
  );
}
