import { useState } from 'react';

/**
 * useFormsState — จัดการแบบฟอร์มสวัสดิการ (Welfare Forms) CRUD: รายการ, เพิ่ม/อัปโหลด PDF
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม (การลบยังคงอยู่ใน confirmDelete
 * ของ useDeleteConfirmation เหมือนเดิม เพราะใช้ modal ยืนยันร่วมกันหลายโดเมน)
 */
export function useFormsState(API_URL, fetch, showSuccess, showError) {
  const [forms, setForms] = useState([]);
  const [formName, setFormName] = useState('');
  const [formFile, setFormFile] = useState(null);
  const [formPage, setFormPage] = useState('');
  const [formSearchQuery, setFormSearchQuery] = useState('');

  const fetchForms = () => {
    fetch(API_URL + '/api/admin/forms')
      .then(res => res.json())
      .then(data => setForms(data))
      .catch(err => console.error("Error fetching forms:", err));
  };

  const handleAddForm = (e) => {
    e.preventDefault();
    if (!formName.trim()) {
      showError("กรุณากรอกชื่อแบบฟอร์ม");
      return;
    }
    if (!formFile) {
      showError("กรุณาเลือกไฟล์ PDF ของแบบฟอร์ม");
      return;
    }

    const headers = {
      'X-Form-Name': encodeURIComponent(formName),
      'X-File-Name': encodeURIComponent(formFile.name),
      'X-Form-Page': formPage || ''
    };

    fetch(API_URL + '/api/admin/forms/upload', {
      method: 'POST',
      headers: headers,
      body: formFile
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
        } else {
          showSuccess(data.message || "บันทึกและอัปโหลดแบบฟอร์มสำเร็จ");
          setFormName('');
          setFormPage('');
          setFormFile(null);
          const fileInput = document.getElementById('form-file-uploader');
          if (fileInput) fileInput.value = '';
          fetchForms();
        }
      })
      .catch(err => showError("เกิดข้อผิดพลาดในการอัปโหลดแบบฟอร์ม"));
  };

  return {
    forms,
    setForms,
    formName,
    setFormName,
    formFile,
    setFormFile,
    formPage,
    setFormPage,
    formSearchQuery,
    setFormSearchQuery,
    fetchForms,
    handleAddForm,
  };
}
