import { useState } from 'react';

/**
 * useUsersState — จัดการบัญชีแอดมิน (User Management) CRUD ทั้งหมด
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
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
            throw new Error(data.detail || "บันทึกข้อมูลไม่สำเร็จ");
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

  return {
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
