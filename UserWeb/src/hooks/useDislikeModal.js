/**
 * TUH Chatbot AI — useDislikeModal Custom Hook
 * จัดการ Modal แจ้งเหตุผลไม่พึงพอใจ (Dislike Feedback Modal):
 * 1. เปิด Modal อัตโนมัติเมื่อผู้ใช้กดปุ่ม Dislike (thumbs-down) ที่ข้อความของบอท
 * 2. ล็อกคำถามเดิมและคำตอบของบอท (Read-only) เพื่อให้ผู้ใช้พิมพ์เหตุผลหรือคำตอบที่ถูกต้อง
 * 3. ส่งข้อมูลความคิดเห็นไปยัง API '/api/admin/feedback/submit'
 */
import { useState } from 'react';
import { API_URL } from '../utils/chatUtils';

export function useDislikeModal() {
  const [showDislikeModal, setShowDislikeModal] = useState(false);
  const [dislikeQuestion, setDislikeQuestion] = useState(''); // คำถามของผู้ใช้
  const [dislikeAnswer, setDislikeAnswer] = useState(''); // คำตอบที่บอทตอบ
  const [dislikeMsgId, setDislikeMsgId] = useState(''); // ID ข้อความที่ถูก dislike
  const [dislikeReason, setDislikeReason] = useState(''); // เหตุผลที่ผู้ใช้ระบุ
  const [dislikeSuccess, setDislikeSuccess] = useState(false); // สถานะส่งสำเร็จ
  const [dislikeError, setDislikeError] = useState(''); // ข้อความแจ้งเตือนข้อผิดพลาด

  /**
   * เปิด Modal ระบุเหตุผลที่ไม่พึงพอใจ พร้อมผูกบริบทคำถาม-คำตอบ
   */
  const openDislikeModal = ({ question, answer, msgId }) => {
    setDislikeQuestion(question || 'ไม่พบคำถาม');
    setDislikeAnswer(answer);
    setDislikeMsgId(msgId);
    setDislikeReason('');
    setDislikeSuccess(false);
    setDislikeError('');
    setShowDislikeModal(true);
  };

  /**
   * ส่งเหตุผลความไม่พึงพอใจไปยัง Backend
   */
  const handleDislikeSubmit = (e) => {
    e.preventDefault();
    if (!dislikeReason.trim()) return;

    setDislikeError('');

    // ยิง API บันทึกข้อมูล Dislike พร้อมเหตุผล
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
        // แสดงข้อความขอบคุณ 1.5 วินาทีแล้วปิด Modal
        setTimeout(() => {
          setShowDislikeModal(false);
          setDislikeSuccess(false);
          setDislikeReason('');
        }, 1500);
      })
      .catch(err => {
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

