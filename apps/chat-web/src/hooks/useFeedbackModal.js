/**
 * TUH Chatbot AI — useFeedbackModal Custom Hook
 * จัดการหน้าต่างแบบประเมินความพึงพอใจ (CSAT Feedback Modal):
 * 1. รองรับทั้งการเปิดประเมินเองจากเมนู (General feedback) และแบบบังคับกรอก (Forced feedback หลังถามครบ 3 ข้อ)
 * 2. ตรวจสอบคะแนนดาว (1-5 ดาว) และความคิดเห็นเพิ่มเติม
 * 3. ส่งข้อมูลไปยัง API '/api/admin/feedback/submit' พร้อมทั้ง Redirect หรือปิด Modal หลังส่งสำเร็จ
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

export function useFeedbackModal() {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0); // คะแนนดาว 1-5
  const [feedbackText, setFeedbackText] = useState(''); // ข้อความเสนอแนะ
  const [feedbackSuccess, setFeedbackSuccess] = useState(false); // สถานะส่งสำเร็จ
  const [feedbackError, setFeedbackError] = useState(''); // ข้อความแจ้งเตือนข้อผิดพลาด
  const [isForcedFeedback, setIsForcedFeedback] = useState(false); // โหมดบังคับกรอก (หลังถามครบ 3 คำถาม)

  // ล้างข้อความ error เดิมทุกครั้งที่เปิดฟอร์มข้อเสนอแนะขึ้นมาใหม่
  useEffect(() => {
    if (showFeedback) {
      setFeedbackError('');
    }
  }, [showFeedback]);

  /**
   * ส่งแบบประเมินความพึงพอใจไปยัง Backend
   */
  const handleFeedbackSubmit = (e) => {
    e.preventDefault();

    // ต้องเลือกคะแนนดาวอย่างน้อย 1 ดาว
    if (feedbackRating < 1) {
      return;
    }

    setFeedbackError('');

    // จัดเตรียม Payload สำหรับส่งไปยัง Backend
    const feedbackData = {
      rating: feedbackRating >= 4 ? 'like' : 'dislike',
      stars: feedbackRating,
      comment: feedbackText,
      query: isForcedFeedback ? 'บังคับกรอกก่อนปิดหน้าต่าง' : 'ความคิดเห็นทั่วไปจากแบบฟอร์ม',
      msgId: `feedback-${Date.now()}`
    };

    // ส่งคำขอแบบ POST ไปยัง Endpoint บันทึก Feedback
    fetch(API_URL + '/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    })
      .then(r => {
        if (!r.ok) throw new Error("HTTP error " + r.status);
        return r.json();
      })
      .then(data => {
        if (!data.success) throw new Error("Feedback submit did not report success");

        // บันทึกสถานะว่าได้ส่งแบบประเมินแล้ว เพื่อไม่ให้เด้งถามซ้ำ
        sessionStorage.setItem('tuh_feedback_submitted', 'true');
        const savedFeedback = localStorage.getItem('tuh_feedback_logs') || '[]';
        try {
          const logs = JSON.parse(savedFeedback);
          logs.push({
            rating: feedbackRating,
            comment: feedbackText,
            timestamp: new Date().toLocaleString('th-TH')
          });
          localStorage.setItem('tuh_feedback_logs', JSON.stringify(logs));
        } catch (err) {
          console.error(err);
        }
        setFeedbackSuccess(true);

        // รอ 2 วินาทีเพื่อให้ผู้ใช้เห็นข้อความขอบคุณ ก่อนปิด Modal หรือ Redirect
        setTimeout(() => {
          setShowFeedback(false);
          setFeedbackSuccess(false);
          setFeedbackRating(0);
          setFeedbackText('');
          if (isForcedFeedback) {
            window.location.href = "https://intranet.hospital.tu.ac.th/";
          }
        }, 2000);
      })
      .catch(err => {
        console.error("Failed to submit feedback comments:", err);
        setFeedbackError('ส่งข้อเสนอแนะไม่สำเร็จ กรุณาลองใหม่อีกครั้ง (เช็คการเชื่อมต่ออินเทอร์เน็ต)');
      });
  };

  return {
    showFeedback, setShowFeedback,
    feedbackRating, setFeedbackRating,
    feedbackText, setFeedbackText,
    feedbackSuccess, feedbackError,
    isForcedFeedback, setIsForcedFeedback,
    handleFeedbackSubmit
  };
}

