/**
 * StatCard — การ์ดสรุปตัวเลขสำคัญ 1 ใบ ในส่วนที่ 1 ของหน้า Dashboard (4 ใบ เกือบเหมือนกันทุก
 * ประการ ต่างกันแค่สี gradient/ไอคอน/ป้ายกำกับ/ตัวเลข/ข้อความท้ายการ์ด) แยกออกมาจาก
 * DashboardPage.jsx เดิม — รับเนื้อหาที่แตกต่างกัน (badge/value/subtitle) เป็น ReactNode
 * ผ่าน props ตรงๆ เพื่อคง JSX เดิมของแต่ละการ์ดไว้ทุกตัวอักษร ไม่ปัดให้เหมือนกันเกินจริง
 */
export default function StatCard({ onClick, gradientClasses, icon, badge, title, value, footerText }) {
  return (
    <div
      onClick={onClick}
      className={`cursor-pointer group relative overflow-hidden rounded-3xl p-5 ${gradientClasses} text-white shadow-md hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300`}
    >
      <div className="absolute right-3 top-3 opacity-20 text-5xl group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      {badge}
      <h4 className="text-sm font-extrabold opacity-95">{title}</h4>
      <div className="mt-2 flex items-baseline gap-2">
        {value}
      </div>
      <div className="mt-3 pt-3 border-t border-white/15 flex items-center justify-between text-xs font-bold opacity-90">
        <span>{footerText}</span>
        <i className="fa-solid fa-arrow-right"></i>
      </div>
    </div>
  );
}
