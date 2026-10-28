import { useState } from 'react';

/**
 * useDepartments — การแยกข้อมูลตามแผนก (หมวดงาน)
 * - isSuperAdmin: SuperAdmin (role 'System Administrator') เห็นทุกแผนก + จัดการส่วนกลางได้
 * - departmentOptions: รายชื่อแผนกจาก GET /api/auth/departments ใช้เป็นตัวเลือกตอนกรอง/ย้ายแผนก
 * - moveToDepartment: SuperAdmin ย้ายเอกสาร / แบบฟอร์ม / คำถามที่ตอบไม่ได้ ไปแผนกอื่น
 *
 * ตัวกรองจริงอยู่ที่ backend (app/services/department_scope.py) — แอดมินแผนกได้ข้อมูลเฉพาะ
 * ของแผนกตัวเองจาก API อยู่แล้ว ฝั่งนี้มีแค่ตัวเลือกให้ SuperAdmin ดูทีละแผนก
 */
export const UNASSIGNED = '__unassigned__';

export function useDepartments(API_URL, fetch, adminUser, showSuccess, showError) {
  const isSuperAdmin = adminUser?.role === 'System Administrator';
  const [departmentOptions, setDepartmentOptions] = useState([]);

  const fetchDepartments = () => {
    fetch(API_URL + '/api/auth/departments')
      .then(r => (r.ok ? r.json() : []))
      .then(data => setDepartmentOptions(Array.isArray(data) ? data : []))
      .catch(err => console.error("Error fetching departments:", err));
  };

  // kind: 'document' | 'form' | 'unanswered' — คืน Promise<boolean>
  const moveToDepartment = (kind, id, department) => {
    const value = department || null;
    let request;
    if (kind === 'document') {
      request = fetch(API_URL + '/api/admin/documents/update_department', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: id, department: value })
      });
    } else if (kind === 'form') {
      request = fetch(API_URL + '/api/admin/forms/update_department', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, department: value })
      });
    } else {
      request = fetch(API_URL + '/api/admin/unanswered/' + encodeURIComponent(id) + '/department', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ department: value })
      });
    }
    return request
      .then(r => {
        if (!r.ok) throw new Error('move failed');
        showSuccess(value ? `ย้ายไปที่ ${value} แล้ว` : 'เปลี่ยนเป็น "ยังไม่ระบุแผนก" แล้ว');
        return true;
      })
      .catch(() => {
        showError('ย้ายแผนกไม่สำเร็จ');
        return false;
      });
  };

  // กรองรายการฝั่งหน้าเว็บตามตัวเลือกของ SuperAdmin ('' = ทุกแผนก)
  const matchesDepartment = (itemDepartment, filter) => {
    if (!filter) return true;
    if (filter === UNASSIGNED) return !itemDepartment;
    return itemDepartment === filter;
  };

  return {
    isSuperAdmin,
    departmentOptions,
    fetchDepartments,
    moveToDepartment,
    matchesDepartment,
  };
}
