import { useState } from 'react';
import { API_URL } from '../utils/chatUtils';

// สถานะของฟอร์มระบุเหตุผลที่ไม่พึงพอใจ (dislike) + การส่งคำอธิบายไปยังส่วนหลังบ้าน
// dislikeMsgId ต้องอยู่ภายในไฟล์นี้เท่านั้น (purely internal) — ใช้ประกอบ payload ตอนส่งฟอร์มเท่านั้น
// ห้ามส่งออกไปเป็น prop ของ <DislikeModal> เด็ดขาด (เหมือนพฤติกรรมเดิมทุกประการ)
export function useDislikeModal() {
  const [showDislikeModal, setShowDislikeModal] = useState(false);
  const [dislikeQuestion, setDislikeQuestion] = useState('');
  const [dislikeAnswer, setDislikeAnswer] = useState('');
  const [dislikeMsgId, setDislikeMsgId] = useState('');
  const [dislikeReason, setDislikeReason] = useState('');
  const [dislikeSuccess, setDislikeSuccess] = useState(false);
  const [dislikeError, setDislikeError] = useState('');

  // เปิดหน้าต่างระบุเหตุผลที่ไม่พึงพอใจ — จุดเดียวที่ตั้งค่า dislikeMsgId ได้ (ผู้เรียกภายนอก เช่น
  // handleLikeMessage ใน App.jsx ไม่มีทางแตะ setter ของ dislikeMsgId ได้โดยตรง)
  const openDislikeModal = ({ question, answer, msgId }) => {
    setDislikeQuestion(question || 'ไม่พบคำถาม');
    setDislikeAnswer(answer);
    setDislikeMsgId(msgId);
    setDislikeReason('');
    setDislikeSuccess(false);
    setDislikeError('');
    setShowDislikeModal(true);
  };

  const handleDislikeSubmit = (e) => {
    e.preventDefault();
    if (!dislikeReason.trim()) return;

    setDislikeError('');

    fetch(API_URL + '/api/admin/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        msgId: dislikeMsgId,
        rating: 'dislike',
        comment: dislikeReason,
        query: dislikeQuestion,
        answer: dislikeAnswer
      })
    })
      .then(r => {
        if (!r.ok) throw new Error("HTTP error " + r.status);
        return r.json();
      })
      .then(data => {
        if (!data.success) throw new Error("Feedback submit did not report success");
        setDislikeSuccess(true);
        setTimeout(() => {
          setShowDislikeModal(false);
          setDislikeSuccess(false);
          setDislikeReason('');
        }, 1500);
      })
      .catch(err => {
        // เดิม .catch() นี้ set success=true เหมือนกัน ทำให้ผู้ใช้เห็นว่าส่งสำเร็จทั้งที่ backend
        // ไม่ได้บันทึกความเห็นไว้เลย (เหตุผลเดียวกับ handleFeedbackSubmit ใน useFeedbackModal.js)
        console.error("Failed to submit dislike explanation:", err);
        setDislikeError('ส่งความคิดเห็นไม่สำเร็จ กรุณาลองใหม่อีกครั้ง (เช็คการเชื่อมต่ออินเทอร์เน็ต)');
      });
  };

  return {
    showDislikeModal, setShowDislikeModal,
    dislikeQuestion, dislikeAnswer,
    dislikeReason, setDislikeReason,
    dislikeSuccess, dislikeError,
    handleDislikeSubmit, openDislikeModal
  };
}
