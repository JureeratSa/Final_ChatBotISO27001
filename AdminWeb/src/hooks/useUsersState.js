import { useState } from 'react';

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * useUsersState — จัดการบัญชีแอดมิน (User Management) CRUD ทั้งหมด
 * แยกออกมาจาก App.jsx เดิม
 */
export function useUsersState(API_URL, fetch, showSuccess, showError) {
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showUserModal, setShowUserModal] = useState(false);
  const [userFormMode, setUserFormMode] = useState('create'); // 'create' | 'edit'
  const [selectedUser, setSelectedUser] = useState(null);
  const [userFormUsername, setUserFormUsername] = useState('');
  const [userFormPassword, setUserFormPassword] = useState('');
  const [userFormDisplayName, setUserFormDisplayName] = useState('');
  const [userFormRole, setUserFormRole] = useState('admin');
  const [userFormIsActive, setUserFormIsActive] = useState(true);
  const [userFormDepartment, setUserFormDepartment] = useState('');

  const departments = Array.from(new Set(users.map(u => u.department).filter(Boolean)));

  const fetchUsers = () => {
    setLoadingUsers(true);
    fetch(API_URL + '/api/auth/users')
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถโหลดข้อมูลบัญชีผู้ใช้ได้");
        return res.json();
      })
      .then(data => setUsers(data))
      .catch(err => console.error("Error fetching users:", err))
      .finally(() => setLoadingUsers(false));
  };

  const handleCreateOrUpdateUser = (e) => {
    e.preventDefault();
    if (!userFormUsername.trim() || !userFormDisplayName.trim()) {
      showError("กรุณากรอกข้อมูล Username และ ชื่อแสดงผล");
      return;
    }

    if (userFormMode === 'create' && !userFormPassword.trim()) {
      showError("กรุณากรอกรหัสผ่านสำหรับผู้ใช้ใหม่");
      return;
    }

    const url = userFormMode === 'create'
      ? API_URL + '/api/auth/users'
      : API_URL + `/api/auth/users/${selectedUser.id}`;
    const method = userFormMode === 'create' ? 'POST' : 'PUT';

    const payload = {
      username: userFormUsername,
      display_name: userFormDisplayName,
      role: userFormRole,
      department: userFormDepartment,
      is_active: userFormIsActive
    };

    if (userFormPassword.trim()) {
      payload.password = userFormPassword;
    }

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            // 422 จาก Pydantic ส่ง detail เป็น list ของ {msg} (เช่น รหัสผ่านไม่ผ่านเกณฑ์) — ดึงข้อความออกมาแสดง
            const detail = Array.isArray(data.detail)
              ? data.detail.map(d => String(d.msg || '').replace(/^Value error, /, '')).join(' / ')
              : data.detail;
            throw new Error(detail || "บันทึกข้อมูลไม่สำเร็จ");
          });
        }
        return res.json();
      })
      .then(() => {
        showSuccess(userFormMode === 'create' ? "สร้างบัญชีแอดมินใหม่สำเร็จ" : "แก้ไขบัญชีแอดมินสำเร็จ");
        setShowUserModal(false);
        fetchUsers();
      })
      .catch(err => showError(err.message || "เกิดข้อผิดพลาดในการบันทึกข้อมูล"));
  };

  // ── นำเข้าหลายคนจาก Excel (backend สร้างรหัสผ่านเริ่มต้นให้ คืนมาครั้งเดียวใน importResult) ──
  const [showImportModal, setShowImportModal] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null); // {created, errors, new_departments}

  const downloadImportTemplate = () => {
    fetch(API_URL + '/api/auth/users/import/template')
      .then(res => {
        if (!res.ok) throw new Error("ดาวน์โหลด template ไม่สำเร็จ");
        return res.blob();
      })
      .then(blob => saveBlob(blob, 'admin_import_template.xlsx'))
      .catch(err => showError(err.message));
  };

  const handleImportUsers = (file) => {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    setImporting(true);
    setImportResult(null);
    fetch(API_URL + '/api/auth/users/import', { method: 'POST', body: form })
      .then(res => res.json().then(data => {
        if (!res.ok) throw new Error(data.detail || "นำเข้าไม่สำเร็จ");
        return data;
      }))
      .then(data => {
        setImportResult(data);
        if (data.created.length) {
          showSuccess(`สร้างบัญชีแอดมินใหม่ ${data.created.length} บัญชีสำเร็จ`);
          fetchUsers();
        }
      })
      .catch(err => showError(err.message || "นำเข้าไม่สำเร็จ"))
      .finally(() => setImporting(false));
  };

  return {
    showImportModal,
    setShowImportModal,
    importing,
    importResult,
    setImportResult,
    downloadImportTemplate,
    handleImportUsers,
    users,
    setUsers,
    loadingUsers,
    showUserModal,
    setShowUserModal,
    userFormMode,
    setUserFormMode,
    selectedUser,
    setSelectedUser,
    userFormUsername,
    setUserFormUsername,
    userFormPassword,
    setUserFormPassword,
    userFormDisplayName,
    setUserFormDisplayName,
    userFormRole,
    setUserFormRole,
    userFormIsActive,
    setUserFormIsActive,
    userFormDepartment,
    setUserFormDepartment,
    departments,
    fetchUsers,
    handleCreateOrUpdateUser,
  };
}
