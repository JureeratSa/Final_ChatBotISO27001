import { useState } from 'react';
import { isPasswordValid } from '../utils/passwordPolicy';

/**
 * useProfile — ฟอร์มเปลี่ยนรหัสผ่านแอดมิน (หน้าโปรไฟล์) เรียก POST /api/admin/password/update
 * แยกออกมาจาก App.jsx เดิม
 *
 * เปลี่ยนรหัสสำเร็จแล้ว backend ทำให้ token เดิมใช้ไม่ได้ (ดู password_policy.token_issued_before_password_change)
 * จึงออกจากระบบให้ทันที แล้วให้ล็อกอินใหม่ด้วยรหัสผ่านใหม่
 */
export function useProfile(API_URL, fetch, showSuccess, showError, handleLogout, username) {
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
    if (!isPasswordValid(newPassword, username)) {
      showError("รหัสผ่านยังไม่ผ่านเงื่อนไขทุกข้อ");
      return;
    }

    fetch(API_URL + '/api/admin/password/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => { throw new Error(data.detail || data.error || "เปลี่ยนรหัสผ่านล้มเหลว") });
        }
        return r.json();
      })
      .then(data => {
        setNewPassword('');
        setConfirmPassword('');
        handleLogout('password_changed');
        showSuccess("เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่ด้วยรหัสผ่านใหม่");
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
