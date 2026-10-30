import { useState } from 'react';
import { saveBlob } from '../hooks/useUsersState';

/**
 * UserImportModal — นำเข้าบัญชีแอดมินหลายคนจาก Excel (ใช้ในหน้า UsersPage)
 * backend สร้างรหัสผ่านเริ่มต้นให้แล้วคืนมาครั้งเดียว — ปิดหน้าต่างแล้วดูรหัสอีกไม่ได้ จึงให้ดาวน์โหลดเก็บไว้ก่อน
 */
export default function UserImportModal({ importing, importResult, onClose, onDownloadTemplate, onImport }) {
  const [file, setFile] = useState(null);
  const [downloaded, setDownloaded] = useState(false);
  const created = importResult?.created || [];
  const errors = importResult?.errors || [];

  const downloadPasswords = () => {
    // CSV + BOM ให้ Excel เปิดภาษาไทยได้ถูกต้อง
    const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const lines = [['ชื่อแสดงผล', 'Username', 'หมวดงาน/แผนก', 'บทบาท', 'รหัสผ่านเริ่มต้น']]
      .concat(created.map(u => [u.display_name, u.username, u.department, u.role, u.password]))
      .map(row => row.map(esc).join(','));
    const stamp = new Date().toISOString().slice(0, 10);
    saveBlob(new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }), `admin_initial_passwords_${stamp}.csv`);
    setDownloaded(true);
  };

  const close = () => {
    if (created.length && !downloaded &&
      !window.confirm('ยังไม่ได้ดาวน์โหลดรหัสผ่านเริ่มต้น — ปิดแล้วจะดูรหัสผ่านอีกไม่ได้ (ต้องรีเซ็ตรหัสทีละคน) ต้องการปิดหรือไม่?')) {
      return;
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-3xl max-h-[90vh] flex flex-col tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
        <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className="fa-solid fa-file-excel text-emerald-500"></i>
            นำเข้าบัญชีแอดมินจากไฟล์ Excel
          </h3>
          <button onClick={close} className="text-slate-500 dark:text-slate-400 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition">
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <div className="p-6 space-y-5 overflow-y-auto custom-scrollbar">
          {created.length === 0 && (
            <>
              <ol className="text-xs font-semibold text-slate-600 dark:text-slate-300 space-y-1.5 list-decimal list-inside">
                <li>
                  ดาวน์โหลด template แล้วกรอก 1 แถวต่อ 1 คน (ชื่อแสดงผล, Username, แผนก, บทบาท) — ไม่ต้องกรอกรหัสผ่าน
                  <button
                    type="button"
                    onClick={onDownloadTemplate}
                    className="ml-2 inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 font-bold transition"
                  >
                    <i className="fa-solid fa-download"></i> ดาวน์โหลด template
                  </button>
                </li>
                <li>อัปโหลดไฟล์ที่กรอกแล้ว ระบบจะสร้างรหัสผ่านเริ่มต้นที่ผ่านเงื่อนไขให้ทุกคน</li>
                <li>ดาวน์โหลดรายชื่อพร้อมรหัสผ่านไปแจ้งแอดมินแต่ละคน — ผู้ใช้ต้องตั้งรหัสใหม่เองตอนเข้าสู่ระบบครั้งแรก</li>
              </ol>

              <label className="flex flex-col items-center justify-center gap-2 p-6 rounded-2xl border-2 border-dashed border-slate-300 dark:border-tuh-purple/30 hover:border-tuh-rose cursor-pointer transition text-center">
                <i className="fa-solid fa-cloud-arrow-up text-2xl text-slate-400"></i>
                <span className="text-sm font-bold text-slate-600 dark:text-slate-300">
                  {file ? file.name : 'คลิกเพื่อเลือกไฟล์ .xlsx'}
                </span>
                <input
                  type="file"
                  accept=".xlsx"
                  className="hidden"
                  // ล้างค่าทุกครั้ง — แก้ไฟล์เดิมแล้วเลือกซ้ำต้องได้ onChange ใหม่ (ไม่งั้นส่งเนื้อหาเก่า/อ่านไฟล์ไม่ได้)
                  onClick={e => { e.target.value = ''; }}
                  onChange={e => setFile(e.target.files[0] || null)}
                />
              </label>
            </>
          )}

          {errors.length > 0 && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30">
              <p className="text-sm font-bold text-rose-600 dark:text-rose-300 mb-2">
                <i className="fa-solid fa-circle-exclamation mr-1"></i>
                ยังไม่ได้สร้างบัญชีใดเลย — กรุณาแก้ไขไฟล์ตามรายการนี้แล้วอัปโหลดใหม่
              </p>
              <ul className="text-xs font-semibold text-rose-600 dark:text-rose-300 space-y-1">
                {errors.map((e, i) => (
                  <li key={i}>{e.row ? `แถว ${e.row}` : ''}{e.username ? ` (${e.username})` : ''}{e.row || e.username ? ': ' : ''}{e.message}</li>
                ))}
              </ul>
            </div>
          )}

          {created.length > 0 && (
            <>
              <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-sm font-bold text-emerald-700 dark:text-emerald-300">
                <i className="fa-solid fa-circle-check mr-1"></i>
                สร้างบัญชีแอดมินใหม่ {created.length} บัญชีสำเร็จ — รหัสผ่านด้านล่างแสดงครั้งเดียว กรุณาดาวน์โหลดเก็บไว้ก่อนปิดหน้าต่าง
                {importResult.new_departments?.length > 0 && (
                  <div className="text-xs font-semibold mt-1 text-amber-600 dark:text-amber-400">
                    แผนกใหม่ที่ยังไม่เคยมีในระบบ: {importResult.new_departments.join(', ')} — ถ้าสะกดผิด แก้ได้ที่ปุ่ม "แก้ไข" ของแต่ละบัญชี
                  </div>
                )}
              </div>
              <div className="overflow-x-auto rounded-2xl border border-slate-100 dark:border-tuh-purple/20">
                <table className="w-full text-left text-xs font-semibold">
                  <thead className="bg-slate-100 dark:bg-tuh-navy/30 text-slate-500 dark:text-slate-400 uppercase">
                    <tr>
                      <th className="px-4 py-2.5">ชื่อแสดงผล</th>
                      <th className="px-4 py-2.5">Username</th>
                      <th className="px-4 py-2.5">แผนก</th>
                      <th className="px-4 py-2.5">รหัสผ่านเริ่มต้น</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-slate-700 dark:text-slate-200">
                    {created.map(u => (
                      <tr key={u.username}>
                        <td className="px-4 py-2">{u.display_name}</td>
                        <td className="px-4 py-2">{u.username}</td>
                        <td className="px-4 py-2">{u.department || (u.role === 'System Administrator' ? 'SuperAdmin' : '-')}</td>
                        <td className="px-4 py-2 font-mono text-sm select-all">{u.password}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-3 p-5 border-t border-slate-100 dark:border-tuh-purple/10">
          <button
            type="button"
            onClick={close}
            className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95 text-xs"
          >
            {created.length ? 'ปิด' : 'ยกเลิก'}
          </button>
          {created.length > 0 ? (
            <button
              type="button"
              onClick={downloadPasswords}
              className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-2.5 px-6 rounded-2xl transition active:scale-[0.98] text-xs flex items-center gap-1.5"
            >
              <i className="fa-solid fa-file-arrow-down"></i> ดาวน์โหลดรายชื่อ + รหัสผ่าน (Excel)
            </button>
          ) : (
            <button
              type="button"
              disabled={!file || importing}
              onClick={() => onImport(file)}
              className="bg-tuh-gradient-2 disabled:opacity-50 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] text-xs flex items-center gap-1.5"
            >
              <i className={`fa-solid ${importing ? 'fa-circle-notch animate-spin' : 'fa-upload'}`}></i>
              {importing ? 'กำลังนำเข้า...' : 'นำเข้า'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
