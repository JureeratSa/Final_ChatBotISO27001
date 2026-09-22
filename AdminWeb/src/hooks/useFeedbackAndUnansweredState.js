import { useState } from 'react';

/**
 * useFeedbackAndUnansweredState — ความพึงพอใจ (feedback), คำถามที่บอทตอบไม่ได้ (unanswered),
 * และ flow ลงทะเบียนคำตอบ FAQ (ทั้งจากคำถามที่ตอบไม่ได้ และแก้ไข FAQ ที่ตั้งไว้ล่วงหน้า)
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 *
 * รับ settings/setSettings มาจาก useSettingsState เพราะ handleSubmitFaq/handleSavePredefinedFaq
 * ต้องแก้ settings.custom_faqs / settings.predefined_faqs แล้วยิง POST /api/admin/settings เหมือนเดิม
 *
 * หมายเหตุ: analysisLoading/analysisResult ยังคงอยู่ (มี consumer คือ AnswerFaqModal ในหน้า
 * Dashboard) แต่ setter ของ 2 ตัวนี้เดิมมีอยู่เฉพาะใน handleOpenFaqModal ซึ่งเป็นโค้ดตายที่ไม่มี
 * ใครเรียกใช้เลย (ตรวจสอบด้วย grep แล้ว) จึงถูกลบทิ้งไปตามแผน — สถานะทั้งสองจึงจะเป็นค่าเริ่มต้น
 * (false / null) เสมอ ซึ่งเป็นพฤติกรรมเดิมที่มีอยู่แล้วก่อนการแยกไฟล์นี้ ไม่ได้เปลี่ยนแปลงเพิ่มเติม
 */
export function useFeedbackAndUnansweredState(API_URL, fetch, showSuccess, showError, settings, setSettings, fetchStats) {
  const [feedback, setFeedback] = useState([]);
  const [unanswered, setUnanswered] = useState([]);

  const [showFaqModal, setShowFaqModal] = useState(false);
  const [currentUnanswered, setCurrentUnanswered] = useState(null);
  const [faqAnswer, setFaqAnswer] = useState('');

  // AI Query Analysis States
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

  // Predefined FAQs Edit States
  const [showEditPredefinedFaqModal, setShowEditPredefinedFaqModal] = useState(false);
  const [selectedPredefinedFaq, setSelectedPredefinedFaq] = useState(null);
  const [predefinedFaqQuestion, setPredefinedFaqQuestion] = useState('');
  const [predefinedFaqAnswer, setPredefinedFaqAnswer] = useState('');
  const [predefinedFaqIcon, setPredefinedFaqIcon] = useState('');

  // Sort and Date Filter States for Unanswered Logs
  const [unansweredSortOrder, setUnansweredSortOrder] = useState('desc'); // 'desc' = newest first, 'asc' = oldest first
  const [unansweredStartDate, setUnansweredStartDate] = useState('');
  const [unansweredEndDate, setUnansweredEndDate] = useState('');

  // นับเฉพาะคำถามที่ยังไม่ได้ตรวจเช็ค (status ตรวจเช็คเรียบร้อยแล้วไม่ต้องนับ)
  const pendingUnansweredCount = unanswered.filter(u => u.status === 'Pending').length;

  const fetchFeedback = () => {
    fetch(API_URL + '/api/admin/feedback')
      .then(r => r.json())
      .then(data => setFeedback(data))
      .catch(err => console.error("Error fetching feedback:", err));
  };

  const fetchUnanswered = () => {
    fetch(API_URL + '/api/admin/unanswered')
      .then(r => r.json())
      .then(data => setUnanswered(data))
      .catch(err => console.error("Error fetching unanswered:", err));
  };

  const handleResolveUnanswered = (id, newStatus = "Resolved") => {
    fetch(API_URL + '/api/admin/unanswered/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
      .then(r => {
        if (!r.ok) throw new Error('update failed');
        return r.json();
      })
      .then(() => {
        showSuccess("อัปเดตสถานะล็อกคำถามเรียบร้อยแล้ว");
        fetchUnanswered();
        fetchStats();
      })
      .catch(err => {
        console.error(err);
        showError("ไม่สามารถอัปเดตสถานะได้");
      });
  };

  const handleSubmitFaq = (e) => {
    e.preventDefault();
    if (!faqAnswer.trim()) return;

    const newFaq = {
      id: `faq-${Date.now()}`,
      question: currentUnanswered.query,
      answer: faqAnswer,
      timestamp: new Date().toLocaleDateString('th-TH')
    };

    // Update settings custom FAQs
    const updatedFaqs = [...(settings.custom_faqs || []), newFaq];
    const updatedSettings = { ...settings, custom_faqs: updatedFaqs };

    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลงทะเบียนคู่มือคำตอบ (FAQ) สำเร็จ บอทจะตอบด้วยคำตอบนี้ในแชททันที");
          setSettings(updatedSettings);
          // Auto resolve the unanswered status
          handleResolveUnanswered(currentUnanswered.id, "Resolved");
          setShowFaqModal(false);
          setCurrentUnanswered(null);
        } else {
          showError("เกิดข้อผิดพลาดในการลงทะเบียนคำตอบ");
        }
      })
      .catch(err => showError("เชื่อมต่อล้มเหลว"));
  };

  const handleOpenEditPredefinedFaqModal = (faq) => {
    setSelectedPredefinedFaq(faq);
    setPredefinedFaqQuestion(faq.question);
    setPredefinedFaqAnswer(faq.answer || faq.response || '');
    setPredefinedFaqIcon(faq.icon || 'fa-circle-question');
    setShowEditPredefinedFaqModal(true);
  };

  const handleSavePredefinedFaq = (e) => {
    e.preventDefault();
    if (!selectedPredefinedFaq) return;

    const updatedPredefinedFaqs = settings.predefined_faqs.map(faq => {
      if (faq.id === selectedPredefinedFaq.id) {
        return {
          ...faq,
          question: predefinedFaqQuestion,
          answer: predefinedFaqAnswer,
          response: predefinedFaqAnswer,
          icon: predefinedFaqIcon || 'fa-circle-question'
        };
      }
      return faq;
    });

    const updatedSettings = {
      ...settings,
      predefined_faqs: updatedPredefinedFaqs
    };

    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("บันทึกคำถามที่พบบ่อย (ปุ่มหน้าแรก) สำเร็จแล้ว");
          setSettings(updatedSettings);
          setShowEditPredefinedFaqModal(false);
          setSelectedPredefinedFaq(null);
        } else {
          showError("บันทึกการเปลี่ยนแปลงล้มเหลว");
        }
      })
      .catch(err => showError("เชื่อมต่อเซิร์ฟเวอร์หลังบ้านล้มเหลว"));
  };

  return {
    feedback,
    setFeedback,
    unanswered,
    setUnanswered,
    showFaqModal,
    setShowFaqModal,
    currentUnanswered,
    setCurrentUnanswered,
    faqAnswer,
    setFaqAnswer,
    analysisLoading,
    analysisResult,
    showEditPredefinedFaqModal,
    setShowEditPredefinedFaqModal,
    selectedPredefinedFaq,
    setSelectedPredefinedFaq,
    predefinedFaqQuestion,
    setPredefinedFaqQuestion,
    predefinedFaqAnswer,
    setPredefinedFaqAnswer,
    predefinedFaqIcon,
    setPredefinedFaqIcon,
    unansweredSortOrder,
    setUnansweredSortOrder,
    unansweredStartDate,
    setUnansweredStartDate,
    unansweredEndDate,
    setUnansweredEndDate,
    pendingUnansweredCount,
    fetchFeedback,
    fetchUnanswered,
    handleResolveUnanswered,
    handleSubmitFaq,
    handleOpenEditPredefinedFaqModal,
    handleSavePredefinedFaq,
  };
}
