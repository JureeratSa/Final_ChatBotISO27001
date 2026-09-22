import { useState } from 'react';

/**
 * useSettingsState — การตั้งค่าระบบ AI แชทบอท (โมเดล/พรอมป์/FAQs ฯลฯ) ผ่าน
 * GET/POST /api/admin/settings แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 */
export function useSettingsState(API_URL, fetch, showSuccess, showError) {
  const [settings, setSettings] = useState({
    gemini_api_key: '',
    model_name: 'gemini-2.5-flash',
    temperature: 0.2,
    max_tokens: 400,
    top_k: 3,
    system_prompt: '',
    welcome_message: '',
    chat_greeting: '',
    custom_faqs: [],
    predefined_faqs: [],
    embedding_tech: 'local_chroma'
  });

  const fetchSettings = () => {
    fetch(API_URL + '/api/admin/settings')
      .then(r => r.json())
      .then(data => {
        // Initialize default empty array for custom_faqs and predefined_faqs if not present
        if (!data.custom_faqs) data.custom_faqs = [];
        if (!data.predefined_faqs) data.predefined_faqs = [];
        setSettings(data);
      })
      .catch(err => console.error("Error fetching settings:", err));
  };

  const handleSaveSettings = (e) => {
    e.preventDefault();
    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("บันทึกการตั้งค่าระบบ AI แชทบอทสำเร็จแล้ว");
          fetchSettings();
        } else {
          showError("บันทึกการตั้งค่าล้มเหลว");
        }
      })
      .catch(err => showError("ไม่สามารถเชื่อมต่อระบบหลังบ้านได้"));
  };

  return {
    settings,
    setSettings,
    fetchSettings,
    handleSaveSettings,
  };
}
