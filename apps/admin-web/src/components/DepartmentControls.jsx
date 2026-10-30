import { useAdminContext } from '../context/AdminContext';
import { UNASSIGNED } from '../hooks/useDepartments';

const selectClass = "tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white";

/**
 * ตัวกรอง "แผนก" บนหัวตาราง — แสดงเฉพาะ SuperAdmin (แอดมินแผนกเห็นแค่แผนกตัวเองอยู่แล้ว)
 */
export function DepartmentFilter({ value, onChange }) {
  const { isSuperAdmin, departmentOptions } = useAdminContext();
  if (!isSuperAdmin) return null;
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">แผนก:</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={selectClass}>
        <option value="">ทุกแผนก</option>
        {departmentOptions.map(d => <option key={d} value={d}>{d}</option>)}
        <option value={UNASSIGNED}>ยังไม่ระบุแผนก</option>
      </select>
    </div>
  );
}

/**
 * ช่อง "แผนก" ในแต่ละแถว — SuperAdmin เลือกย้ายแผนกได้ทันที, แอดมินแผนกไม่แสดงคอลัมน์นี้
 * onMove(department) ต้องคืน Promise (ผู้เรียก refetch รายการเองหลังย้ายสำเร็จ)
 */
export function DepartmentCell({ value, onMove }) {
  const { isSuperAdmin, departmentOptions } = useAdminContext();
  if (!isSuperAdmin) return null;
  // แผนกที่ไม่มีแอดมินแล้วยังต้องเลือกค้างไว้ได้ ไม่งั้น select จะเด้งไปค่าแรกเอง
  const options = value && !departmentOptions.includes(value) ? [value, ...departmentOptions] : departmentOptions;
  return (
    <select
      value={value || ''}
      onChange={(e) => onMove(e.target.value)}
      className={`${selectClass} ${value ? '' : 'text-amber-600 dark:text-amber-400'}`}
      title="ย้ายไปแผนกอื่น"
    >
      <option value="">ยังไม่ระบุแผนก</option>
      {options.map(d => <option key={d} value={d}>{d}</option>)}
    </select>
  );
}
