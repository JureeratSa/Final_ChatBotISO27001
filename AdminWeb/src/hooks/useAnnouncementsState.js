import { useState } from 'react';

/**
 * useAnnouncementsState — ประกาศระบบ (Announcements) CRUD ทั้งหมด
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 *
 * รับ setDeleteModalState มาจาก App.jsx (state ของ modal ยืนยันลบที่ใช้ร่วมกันหลายโดเมน)
 * เพราะ handleDeleteAnnouncement ต้องปิด modal เองใน .finally() เหมือนโค้ดเดิมทุกประการ
 */
export function useAnnouncementsState(API_URL, fetch, showSuccess, showError, setDeleteModalState) {
  const [announcements, setAnnouncements] = useState([]);
  const [annTitle, setAnnTitle] = useState('');
  const [annContent, setAnnContent] = useState('');
  const [annStartDate, setAnnStartDate] = useState('');
  const [annEndDate, setAnnEndDate] = useState('');
  const [annFilter, setAnnFilter] = useState('all');
  const [editingAnnId, setEditingAnnId] = useState(null);
  const [isAnnFormOpen, setIsAnnFormOpen] = useState(false);
  const [annPinned, setAnnPinned] = useState(false);
  const [annCategory, setAnnCategory] = useState('');

  const fetchAnnouncements = () => {
    fetch(API_URL + '/api/admin/announcements')
      .then(res => res.json())
      .then(data => setAnnouncements(data))
      .catch(err => console.error("Error fetching announcements:", err));
  };

  const handleCreateAnnouncement = (e) => {
    e.preventDefault();
    if (!annTitle.trim() || !annContent.trim() || !annStartDate || !annEndDate) {
      showError("กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง");
      return;
    }
    if (new Date(annStartDate) > new Date(annEndDate)) {
      showError("วันเริ่มประกาศต้องไม่มากกว่าวันสิ้นสุดประกาศ");
      return;
    }

    const isEdit = editingAnnId !== null;
    const url = isEdit
      ? API_URL + '/api/admin/announcements/update'
      : API_URL + '/api/admin/announcements/create';

    const payload = {
      title: annTitle,
      content: annContent,
      start_date: annStartDate,
      end_date: annEndDate,
      category: annCategory,
      pinned: annPinned
    };

    if (isEdit) {
      payload.id = editingAnnId;
    }

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
        } else {
          showSuccess(isEdit ? "แก้ไขประกาศสำเร็จ" : "สร้างประกาศสำเร็จ");
          setAnnTitle('');
          setAnnContent('');
          setAnnStartDate('');
          setAnnEndDate('');
          setAnnCategory('');
          setEditingAnnId(null);
          setAnnPinned(false);
          setIsAnnFormOpen(false);
          fetchAnnouncements();
        }
      })
      .catch(err => showError(isEdit ? "เกิดข้อผิดพลาดในการแก้ไขประกาศ" : "เกิดข้อผิดพลาดในการสร้างประกาศ"));
  };

  const handleEditAnnouncement = (ann) => {
    setAnnTitle(ann.title);
    setAnnContent(ann.content);
    setAnnStartDate(ann.start_date);
    setAnnEndDate(ann.end_date);
    setEditingAnnId(ann.id);
    setAnnPinned(ann.pinned || false);
    setAnnCategory(ann.category || '');
    setIsAnnFormOpen(true);
  };

  const handleCancelEditAnnouncement = () => {
    setAnnTitle('');
    setAnnContent('');
    setAnnStartDate('');
    setAnnEndDate('');
    setAnnCategory('');
    setEditingAnnId(null);
    setAnnPinned(false);
    setIsAnnFormOpen(false);
  };

  const handleDeleteAnnouncement = (annId) => {
    fetch(API_URL + '/api/admin/announcements/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: annId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลบประกาศสำเร็จ");
          fetchAnnouncements();
        } else {
          showError("ลบไม่สำเร็จ");
        }
      })
      .catch(err => showError("เกิดข้อผิดพลาดในการลบประกาศ"))
      .finally(() => {
        setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
      });
  };

  return {
    announcements,
    setAnnouncements,
    annTitle,
    setAnnTitle,
    annContent,
    setAnnContent,
    annStartDate,
    setAnnStartDate,
    annEndDate,
    setAnnEndDate,
    annFilter,
    setAnnFilter,
    editingAnnId,
    setEditingAnnId,
    isAnnFormOpen,
    setIsAnnFormOpen,
    annPinned,
    setAnnPinned,
    annCategory,
    setAnnCategory,
    fetchAnnouncements,
    handleCreateAnnouncement,
    handleEditAnnouncement,
    handleCancelEditAnnouncement,
    handleDeleteAnnouncement,
  };
}
