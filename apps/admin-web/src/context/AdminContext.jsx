import { createContext, useContext } from 'react';

/**
 * AdminContext — ที่เก็บ state/handler ทั้งหมดของ App() แชร์ให้ทุก page component เข้าถึงได้
 * โดยไม่ต้อง prop-drilling ทีละตัว (เดิม App.jsx เป็นไฟล์เดียว 5,400+ บรรทัด มี useState เกือบ
 * 100 ตัวปนกับ JSX render ของทุกแท็บ — แยกไฟล์แล้ว แต่ยังคง "แหล่งความจริงเดียว" (single
 * source of truth) ของ state ไว้ที่ App.jsx เหมือนเดิมทุกประการ ไม่ได้ย้าย state ไปไหน
 * แค่แชร์การเข้าถึงผ่าน context แทนการส่ง props ทีละตัว)
 *
 * ทุก page ดึงเฉพาะค่าที่ตัวเองใช้ผ่าน useAdminContext() — ไม่มีการเปลี่ยนพฤติกรรมใดๆ
 * เทียบกับตอนที่โค้ดทั้งหมดอยู่ในไฟล์เดียว
 */
export const AdminContext = createContext(null);

export function useAdminContext() {
  const ctx = useContext(AdminContext);
  if (!ctx) {
    throw new Error('useAdminContext ต้องถูกเรียกภายใน <AdminContext.Provider> เท่านั้น');
  }
  return ctx;
}
