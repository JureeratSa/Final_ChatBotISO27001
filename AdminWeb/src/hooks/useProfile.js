import { useState } from 'react';

/**
 * useProfile — ฟอร์มเปลี่ยนรหัสผ่านแอดมิน (หน้าโปรไฟล์) เรียก POST /api/admin/password/update
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 */
export function useProfile(API_URL, fetch, showSuccess, showError) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password Visibility Toggle States (profile form only)
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleUpdatePassword = (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showError("รหัสผ่านไม่ตรงกัน");
      return;
    }
    if (newPassword.length < 4) {
      showError("รหัสผ่านสั้นเกินไป");
      return;
    }

    fetch(API_URL + '/api/admin/password/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => { throw new Error(data.error || "เปลี่ยนรหัสผ่านล้มเหลว") });
        }
        return r.json();
      })
      .then(data => {
        showSuccess("เปลี่ยนรหัสผ่านแอดมินสำเร็จแล้ว (มีผลในการเข้าสู่ระบบครั้งถัดไป)");
        setNewPassword('');
        setConfirmPassword('');
      })
      .catch(err => {
        showError(err.message);
      });
  };

  return {
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,
    showNewPassword,
    setShowNewPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    handleUpdatePassword,
  };
}
