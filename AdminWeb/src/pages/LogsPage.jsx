import { useAdminContext } from '../context/AdminContext';

/**
 * LogsPage — แท็บ "คำถามที่บอทตอบไม่ได้" ตารางรายการคำถามค้างพร้อมตัวกรองช่วงวันที่และการเรียงลำดับ
 * และปุ่มติ๊กแก้ไข/ไม่แก้ไข
 */
export default function LogsPage() {
  const {
    handleResolveUnanswered,
    parseTimestamp,
    setUnansweredEndDate,
    setUnansweredSortOrder,
    setUnansweredStartDate,
    unanswered,
    unansweredEndDate,
    unansweredSortOrder,
    unansweredStartDate,
  } = useAdminContext();

  return (
    <div className="space-y-6 animate-slide-in">
      <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-triangle-exclamation text-tuh-rose"></i> รายชื่อคำถามที่บอทตอบไม่ได้ ({unanswered.length})</h3>

          {/* Date filtering & sorting controls for unanswered logs */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Sort Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เรียงตามวัน:</span>
              <select
                value={unansweredSortOrder}
                onChange={(e) => setUnansweredSortOrder(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              >
                <option value="desc">ใหม่ไปเก่า (ล่าสุด)</option>
                <option value="asc">เก่าไปใหม่</option>
              </select>
            </div>

            {/* Start Date */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เริ่มต้น:</span>
              <input
                type="date"
                value={unansweredStartDate}
                onChange={(e) => setUnansweredStartDate(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              />
            </div>

            {/* End Date */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">สิ้นสุด:</span>
              <input
                type="date"
                value={unansweredEndDate}
                onChange={(e) => setUnansweredEndDate(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              />
            </div>

            {/* Reset Button */}
            {(unansweredStartDate || unansweredEndDate) && (
              <button
                onClick={() => {
                  setUnansweredStartDate('');
                  setUnansweredEndDate('');
                }}
                className="text-xs font-bold text-rose-500 hover:text-rose-600 transition"
              >
                ล้างค่า
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                <th className="px-6 py-4">ข้อความคำถาม</th>
                <th className="px-6 py-4 text-center">ถามซ้ำ (จำนวน)</th>
                <th className="px-6 py-4 whitespace-nowrap">ถามล่าสุดเมื่อ</th>
                <th className="px-6 py-4 text-center">สถานะ</th>
                <th className="px-6 py-4 text-center">เครื่องมือแก้ไข</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
              {(() => {
                let processed = [...unanswered];

                // Filter by date range if specified
                if (unansweredStartDate) {
                  const start = new Date(unansweredStartDate);
                  start.setHours(0, 0, 0, 0);
                  processed = processed.filter(log => {
                    const d = parseTimestamp(log.timestamp);
                    return d >= start;
                  });
                }
                if (unansweredEndDate) {
                  const end = new Date(unansweredEndDate);
                  end.setHours(23, 59, 59, 999);
                  processed = processed.filter(log => {
                    const d = parseTimestamp(log.timestamp);
                    return d <= end;
                  });
                }

                // Sort by date
                processed.sort((a, b) => {
                  const dateA = parseTimestamp(a.timestamp);
                  const dateB = parseTimestamp(b.timestamp);
                  return unansweredSortOrder === 'desc' ? dateB - dateA : dateA - dateB;
                });

                if (processed.length === 0) {
                  return (
                    <tr>
                      <td colSpan="5" className="px-6 py-8 text-center text-slate-500 dark:text-slate-400 font-bold">
                        {unanswered.length === 0 ? 'ไม่มีคำถามที่ค้างการตอบในขณะนี้' : 'ไม่พบรายการที่ตรงกับเงื่อนไขเวลาที่ระบุ'}
                      </td>
                    </tr>
                  );
                }

                return processed.map(log => {
                  const isPending = log.status === 'Pending';
                  return (
                    <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                      <td className="px-6 py-4 font-bold text-slate-800 dark:text-slate-100">
                        {log.query}
                      </td>
                      <td className="px-6 py-4 text-center font-black">
                        {log.count} ครั้ง
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {log.timestamp}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {isPending ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-500 dark:text-rose-400 border border-rose-500/20 dark:border-rose-400/20 whitespace-nowrap">
                            <i className="fa-solid fa-clock-rotate-left"></i>
                            รอการตรวจเช็ค
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500 whitespace-nowrap">
                            <i className="fa-solid fa-circle-check"></i>
                            ตรวจเช็คเรียบร้อย
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-4 whitespace-nowrap">
                          <label className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={log.status === 'Resolved'}
                              onChange={() => handleResolveUnanswered(log.id, "Resolved")}
                              className="w-4 h-4 rounded accent-emerald-500 cursor-pointer"
                            />
                            แก้ไข
                          </label>
                          <label className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={log.status === 'Ignored'}
                              onChange={() => handleResolveUnanswered(log.id, "Ignored")}
                              className="w-4 h-4 rounded accent-slate-400 cursor-pointer"
                            />
                            ไม่แก้ไข
                          </label>
                        </div>
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
