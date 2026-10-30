import { useEffect, useState } from 'react';
import { useAdminContext } from '../context/AdminContext';

/**
 * AuditLogsPage — แท็บ "บันทึกการเข้าใช้งาน" (เฉพาะ SuperAdmin)
 * แสดงการเข้าสู่ระบบ / ออกจากระบบ และการแก้ไขข้อมูลของแอดมินทุกคน จาก GET /api/admin/audit-logs
 * (backend ไม่เก็บเนื้อหาคำขอ — มีแค่ว่าเรียก API ไหน ผลเป็นอย่างไร จากเครื่อง/IP ไหน)
 */
const ACTION_LABELS = {
  login_success: { text: 'เข้าสู่ระบบ', cls: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400', icon: 'fa-right-to-bracket' },
  login_failed: { text: 'เข้าสู่ระบบไม่สำเร็จ', cls: 'bg-rose-500/10 text-rose-500', icon: 'fa-triangle-exclamation' },
  logout: { text: 'ออกจากระบบ', cls: 'bg-slate-500/10 text-slate-500 dark:text-slate-400', icon: 'fa-right-from-bracket' },
  change: { text: 'แก้ไขข้อมูล', cls: 'bg-sky-500/10 text-sky-600 dark:text-sky-400', icon: 'fa-pen-to-square' },
};

// คำอธิบายภาษาไทยของ API ที่ถูกเรียก (จับจาก path ขึ้นต้น) — ไม่ตรงรายการไหนแสดง METHOD path แทน
const PATH_LABELS = [
  ['/api/admin/documents/upload', 'อัปโหลดเอกสาร'],
  ['/api/admin/documents/approve', 'อนุมัติขั้นตอนเอกสาร'],
  ['/api/admin/documents/toggle', 'เปิด/ปิดใช้งานเอกสาร'],
  ['/api/admin/documents/delete', 'ลบเอกสาร'],
  ['/api/admin/documents/update_department', 'ย้ายแผนกเอกสาร'],
  ['/api/admin/documents/update_details', 'แก้ไขชื่อเอกสาร'],
  ['/api/admin/documents/update_exclude', 'แก้ไขหน้าที่ละเว้น'],
  ['/api/admin/documents/update_content', 'แก้ไขเนื้อหาเอกสาร'],
  ['/api/admin/documents', 'แก้ไขเอกสาร'],
  ['/api/admin/forms/upload', 'อัปโหลดแบบฟอร์ม'],
  ['/api/admin/forms/delete', 'ลบแบบฟอร์ม'],
  ['/api/admin/forms/update_department', 'ย้ายแผนกแบบฟอร์ม'],
  ['/api/admin/forms', 'แก้ไขแบบฟอร์ม'],
  ['/api/admin/unanswered/analyze', 'วิเคราะห์คำถามด้วย AI'],
  ['/api/admin/unanswered', 'จัดการคำถามที่ตอบไม่ได้'],
  ['/api/admin/custom_faqs', 'เพิ่มคำตอบ FAQ'],
  ['/api/admin/settings', 'แก้ไขตั้งค่าระบบ AI'],
  ['/api/admin/rebuild', 'Rebuild ฐานข้อมูลค้นหา'],
  ['/api/admin/announcements', 'จัดการประกาศ'],
  ['/api/admin/feedback', 'ลบความพึงพอใจ'],
  ['/api/admin/password/update', 'เปลี่ยนรหัสผ่านตัวเอง'],
  ['/api/auth/users', 'จัดการบัญชีแอดมิน'],
];

const describePath = (log) => {
  if (log.action !== 'change') return '';
  const found = PATH_LABELS.find(([prefix]) => (log.path || '').startsWith(prefix));
  return found ? found[1] : `${log.method} ${log.path}`;
};

const describeDetail = (log) => {
  const d = log.detail || {};
  const parts = [];
  if (d.reason === 'invalid_credentials') parts.push('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง');
  if (d.reason === 'account_disabled') parts.push('บัญชีถูกระงับ');
  if (d.reason === 'idle') parts.push('ระบบออกให้อัตโนมัติ (ไม่มีการใช้งาน)');
  if (d.target_user) parts.push(`บัญชี: ${d.target_user}`);
  if (d.changes) {
    Object.entries(d.changes).forEach(([field, v]) => {
      parts.push(Array.isArray(v) ? `${field}: ${v[0] ?? '-'} → ${v[1] ?? '-'}` : `${field}: ${v}`);
    });
  }
  // รายการที่ถูกเพิ่ม/ลบ/แก้ (backend ใส่ผ่าน add_audit_detail)
  if (d.document) parts.push(`เอกสาร: ${d.document_name && d.document_name !== d.document ? `${d.document_name} (${d.document})` : d.document}`);
  if (d.form) parts.push(`แบบฟอร์ม: ${d.form}`);
  if (d.announcement) parts.push(`ประกาศ: ${d.announcement}`);
  if (d.faq_question) parts.push(`คำถาม FAQ: ${d.faq_question}`);
  if (d.question) parts.push(`คำถาม: ${d.question}`);
  if (d.from_department || d.to_department) parts.push(`แผนก: ${d.from_department} → ${d.to_department}`);
  else if (d.department && (d.document || d.form || d.question)) parts.push(`แผนก: ${d.department}`);
  if (d.from_status || d.to_status) parts.push(`สถานะ: ${d.from_status ?? '-'} → ${d.to_status ?? '-'}`);
  if (d.new_display_name) parts.push(`ชื่อใหม่: ${d.new_display_name}`);
  if (d.exclude_pages) parts.push(`ละเว้นหน้า: ${d.exclude_pages}`);
  if (d.content_type) parts.push(`แก้เนื้อหา: ${d.content_type}`);
  if (d.changed_fields) parts.push(`ช่องที่แก้: ${d.changed_fields.join(', ')}`);
  if (d.replaced_existing) parts.push('อัปโหลดทับไฟล์เดิม');
  return parts.join(' · ');
};

// สรุป User-Agent เป็น "เบราว์เซอร์ / ระบบปฏิบัติการ" ให้อ่านง่าย (ค่าเต็มอยู่ใน tooltip และ CSV)
const summarizeUserAgent = (ua) => {
  if (!ua) return '-';
  const browser = /Edg\//.test(ua) ? 'Edge' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox'
    : /Safari\//.test(ua) ? 'Safari' : ua.split(' ')[0];
  const os = /Windows/.test(ua) ? 'Windows' : /Android/.test(ua) ? 'Android' : /iPhone|iPad/.test(ua) ? 'iOS'
    : /Mac OS/.test(ua) ? 'macOS' : /Linux/.test(ua) ? 'Linux' : '';
  return os ? `${browser} / ${os}` : browser;
};

const inputClass = "tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white";

export default function AuditLogsPage() {
  const { API_URL, fetch, parseTimestamp } = useAdminContext();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState('');
  const [userQuery, setUserQuery] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchLogs = () => {
    setLoading(true);
    fetch(API_URL + '/api/admin/audit-logs?limit=5000')
      .then(r => (r.ok ? r.json() : []))
      .then(data => setLogs(Array.isArray(data) ? data : []))
      .catch(err => console.error("Error fetching audit logs:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const q = userQuery.trim().toLowerCase();
  const filtered = logs.filter(log => {
    if (actionFilter && log.action !== actionFilter) return false;
    if (q && !`${log.username || ''} ${log.department || ''} ${log.ip_address || ''}`.toLowerCase().includes(q)) return false;
    const d = parseTimestamp(log.timestamp);
    if (startDate) {
      const s = new Date(startDate); s.setHours(0, 0, 0, 0);
      if (d < s) return false;
    }
    if (endDate) {
      const e = new Date(endDate); e.setHours(23, 59, 59, 999);
      if (d > e) return false;
    }
    return true;
  });

  const downloadCSV = () => {
    if (filtered.length === 0) return;
    const headers = ["วันเวลา", "ผู้ใช้", "แผนก", "เหตุการณ์", "รายการ", "รายละเอียด", "ผลลัพธ์ (HTTP)", "IP", "อุปกรณ์/เบราว์เซอร์", "Method", "Path"];
    const rows = filtered.map(log => [
      log.timestamp, log.username, log.department, ACTION_LABELS[log.action]?.text || log.action,
      describePath(log), describeDetail(log), log.status_code, log.ip_address, log.user_agent, log.method, log.path
    ]);
    const csvContent = [
      "﻿" + headers.map(h => `"${h.replace(/"/g, '""')}"`).join(","),
      ...rows.map(row => row.map(val => `"${String(val ?? '').replace(/"/g, '""')}"`).join(","))
    ].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `admin_audit_log_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-slide-in">
      <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-extrabold flex items-center gap-2">
              <i className="fa-solid fa-shield-halved text-tuh-rose"></i> บันทึกการเข้าใช้งานของแอดมิน ({filtered.length})
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
              การเข้าสู่ระบบ ออกจากระบบ และการแก้ไขข้อมูลทุกครั้ง — ไม่เก็บรหัสผ่านหรือเนื้อหาที่ส่งเข้ามา
            </p>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={fetchLogs}
              className="tuh-glass-2 font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs text-tuh-navy dark:text-white"
            >
              <i className={`fa-solid fa-rotate ${loading ? 'animate-spin' : ''}`}></i> โหลดใหม่
            </button>
            <button
              onClick={downloadCSV}
              disabled={filtered.length === 0}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs shadow-sm hover:shadow"
            >
              <i className="fa-solid fa-file-csv"></i> ดาวน์โหลด CSV
            </button>
          </div>
        </div>

        <div className="px-5 py-3.5 bg-slate-50/50 dark:bg-tuh-navy/10 border-b border-slate-100 dark:border-tuh-purple/10 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เหตุการณ์:</span>
            <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} className={inputClass}>
              <option value="">ทั้งหมด</option>
              {Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v.text}</option>)}
            </select>
          </div>
          <input
            type="text"
            placeholder="ค้นหาผู้ใช้ / แผนก / IP..."
            value={userQuery}
            onChange={(e) => setUserQuery(e.target.value)}
            className={`${inputClass} w-56`}
          />
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เริ่มต้น:</span>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={inputClass} />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">สิ้นสุด:</span>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={inputClass} />
          </div>
          {(actionFilter || userQuery || startDate || endDate) && (
            <button
              onClick={() => { setActionFilter(''); setUserQuery(''); setStartDate(''); setEndDate(''); }}
              className="text-xs font-bold text-rose-500 hover:text-rose-600 transition"
            >
              ล้างค่า
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[900px]">
            <thead>
              <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                <th className="px-5 py-4 whitespace-nowrap">วันเวลา</th>
                <th className="px-5 py-4">ผู้ใช้</th>
                <th className="px-5 py-4">เหตุการณ์</th>
                <th className="px-5 py-4">รายละเอียด</th>
                <th className="px-5 py-4 text-center">ผลลัพธ์</th>
                <th className="px-5 py-4">IP / อุปกรณ์</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-slate-500 dark:text-slate-400 font-bold">
                    {loading ? 'กำลังโหลด...' : logs.length === 0 ? 'ยังไม่มีบันทึกการเข้าใช้งาน' : 'ไม่พบรายการที่ตรงกับตัวกรอง'}
                  </td>
                </tr>
              ) : filtered.slice(0, 1000).map(log => {
                const label = ACTION_LABELS[log.action] || { text: log.action, cls: 'bg-slate-500/10 text-slate-500', icon: 'fa-circle' };
                const ok = log.status_code && log.status_code < 400;
                const what = describePath(log);
                const detail = describeDetail(log);
                return (
                  <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition align-top">
                    <td className="px-5 py-3.5 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">{log.timestamp}</td>
                    <td className="px-5 py-3.5">
                      <div className="font-bold text-tuh-navy dark:text-white">{log.username || '-'}</div>
                      {log.department && <div className="text-[11px] text-slate-500 dark:text-slate-400">{log.department}</div>}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold whitespace-nowrap ${label.cls}`}>
                        <i className={`fa-solid ${label.icon}`}></i> {label.text}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs">
                      {what && <div className="font-bold text-tuh-navy dark:text-slate-100">{what}</div>}
                      {detail && <div className="text-slate-500 dark:text-slate-400 mt-0.5">{detail}</div>}
                      {!what && !detail && <span className="text-slate-400">-</span>}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <span className={`text-xs font-black ${ok ? 'text-emerald-500' : 'text-rose-500'}`} title={`HTTP ${log.status_code}`}>
                        {ok ? 'สำเร็จ' : log.status_code === 403 ? 'ไม่มีสิทธิ์' : 'ไม่สำเร็จ'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500 dark:text-slate-400" title={log.user_agent || ''}>
                      <div className="font-bold text-tuh-navy dark:text-slate-200">{log.ip_address || '-'}</div>
                      <div>{summarizeUserAgent(log.user_agent)}</div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length > 1000 && (
            <p className="px-5 py-3 text-xs font-bold text-slate-500 dark:text-slate-400">
              แสดง 1,000 รายการล่าสุดจาก {filtered.length} รายการ — ดาวน์โหลด CSV เพื่อดูทั้งหมด
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
