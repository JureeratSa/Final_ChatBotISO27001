import { useState, useEffect } from 'react';
import { API_URL } from '../utils/chatUtils';

// สถานะของฟอร์มแสดงความคิดเห็น (ทั้งแบบเปิดเองจากเมนู และแบบบังคับกรอกหลังถามครบ 3 ข้อ) +
// การส่งข้อเสนอแนะไปยังส่วนหลังบ้าน
export function useFeedbackModal() {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [feedbackError, setFeedbackError] = useState('');
  const [isForcedFeedback, setIsForcedFeedback] = useState(false);

  // ล้างข้อความ error เดิมทุกครั้งที่เปิดฟอร์มข้อเสนอแนะขึ้นมาใหม่ กันไม่ให้ error ค้างจากการส่งครั้งก่อน
  useEffect(() => {
    if (showFeedback) {
      setFeedbackError('');
    }
  }, [showFeedback]);

  const handleFeedbackSubmit = (e) => {
    e.preventDefault();

    if (feedbackRating < 1) {
      return; // ต้องเลือกจำนวนดาวก่อนส่ง ป้องกันข้อมูลคะแนนที่ไม่ได้มาจากผู้ใช้จริง
    }

    setFeedbackError('');

    const feedbackData = {
      rating: feedbackRating >= 4 ? 'like' : 'dislike',
      stars: feedbackRating,
      comment: feedbackText,
      query: isForcedFeedback ? 'บังคับกรอกก่อนปิดหน้าต่าง' : 'ความคิดเห็นทั่วไปจากแบบฟอร์ม',
      msgId: `feedback-${Date.now()}`
    };

    // หมายเหตุ: ต้องเช็ค response.ok/data.success ก่อนถือว่าสำเร็จ — เดิม fetch() จะ resolve
    // ปกติแม้ backend ตอบ error (4xx/5xx) และ .catch() (เช่น เน็ตหลุด/CORS) ก็ยัง set success=true
    // อยู่ดี ทำให้ผู้ใช้เห็นข้อความ "ส่งเรียบร้อย" ทั้งที่คะแนนดาวไม่ถูกบันทึกลง DB จริง และปิด/รีไดเรกต์
    // หน้าไปเลยหลัง 2 วิ โดยผู้ใช้ไม่มีทางรู้เลยว่าข้อมูลหาย
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
