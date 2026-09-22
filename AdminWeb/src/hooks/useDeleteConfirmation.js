/**
 * useDeleteConfirmation — ตัว "จ่ายงาน" (dispatcher) ของ modal ยืนยันการลบที่ใช้ร่วมกันทุกแท็บ
 * (เอกสาร/แบบฟอร์ม/ประกาศ/ผู้ใช้) โดยดูจาก deleteModalState.type แล้วเรียก endpoint ลบที่ถูกต้อง
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 *
 * หมายเหตุ (การตัดสินใจทางวิศวกรรม): deleteModalState/setDeleteModalState เอง ยังคงเป็น state
 * เล็กๆ ที่ประกาศตรงใน App.jsx (ไม่มี effect ของตัวเอง ใช้ร่วมกันหลายโดเมน) เพราะ
 * useAnnouncementsState ก็ต้องใช้ setDeleteModalState ภายใน handleDeleteAnnouncement ด้วย
 * — ฟังก์ชัน confirmDelete ที่นี่รับ deleteModalState/setDeleteModalState เข้ามาเป็นพารามิเตอร์
 * แทนการ own state เอง เพื่อเลี่ยงปัญหา circular dependency ระหว่าง 2 hook (ดูรายละเอียดในรายงานสรุป)
 */
export function useDeleteConfirmation({
  API_URL,
  fetch,
  showSuccess,
  showError,
  deleteModalState,
  setDeleteModalState,
  fetchDocuments,
  fetchStats,
  fetchForms,
  fetchUsers,
  handleDeleteAnnouncement,
}) {
  const confirmDelete = () => {
    if (!deleteModalState.type) return;
    if (deleteModalState.type === 'document') {
      fetch(API_URL + '/api/admin/documents/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: deleteModalState.targetId })
      })
        .then(r => r.json())
        .then(data => {
          if (data.success) {
            showSuccess("ลบเอกสารและเริ่มปรับปรุงฐานข้อมูลดัชนีเรียบร้อยแล้ว");
            fetchDocuments();
            fetchStats();
          } else {
            showError("เกิดข้อผิดพลาดในการลบเอกสาร");
          }
        })
        .catch(err => showError("ลบเอกสารไม่สำเร็จ"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    } else if (deleteModalState.type === 'form') {
      fetch(API_URL + '/api/admin/forms/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: deleteModalState.targetId })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showSuccess("ลบแบบฟอร์มสำเร็จ");
            fetchForms();
          } else {
            showError("ลบไม่สำเร็จ");
          }
        })
        .catch(err => showError("เกิดข้อผิดพลาดในการลบ"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    } else if (deleteModalState.type === 'announcement') {
      handleDeleteAnnouncement(deleteModalState.targetId);
    } else if (deleteModalState.type === 'user') {
      fetch(API_URL + `/api/auth/users/${deleteModalState.targetId}`, {
        method: 'DELETE'
      })
        .then(res => {
          if (res.status === 204 || res.ok) {
            showSuccess("ลบบัญชีแอดมินเรียบร้อยแล้ว");
            fetchUsers();
          } else {
            return res.json().then(data => {
              throw new Error(data.detail || "ไม่สามารถลบผู้ใช้นี้ได้");
            });
          }
        })
        .catch(err => showError(err.message || "เกิดข้อผิดพลาดในการลบบัญชี"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    }
  };

  return { confirmDelete };
}
