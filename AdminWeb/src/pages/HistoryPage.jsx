import { useAdminContext } from '../context/AdminContext';

/**
 * HistoryPage — แท็บ "ประวัติการตอบของบอท" สรุปจำนวนคำถาม ตัวกรองช่วงเวลา และตาราง
 * รายการคำถาม-คำตอบพร้อมดาวน์โหลด CSV — แยกออกมาจาก App.jsx เดิม
 */
export default function HistoryPage() {
  const {
    API_URL,
    chunksMap,
    downloadCSV,
    filteredHistory,
    history,
    historyEndDate,
    historyLimit,
    historyPeriod,
    historySortOrder,
    historyStartDate,
    loadingHistory,
    parseTimestamp,
    setHistoryEndDate,
    setHistoryLimit,
    setHistoryPeriod,
    setHistorySortOrder,
    setHistoryStartDate,
  } = useAdminContext();

  return (
    <div className="space-y-6 animate-slide-in">
      {/* TOP SUMMARY CARDS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metric Card: Questions Count */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm flex items-center justify-between col-span-1">
          <div className="space-y-1">
            <span className="text-[15px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">คำถามทั้งหมดที่โดนถาม</span>
            <h3 className="text-3xl font-black tracking-tight text-sky-500">
              {filteredHistory.length} <span className="text-[15px] font-bold text-slate-500 dark:text-slate-400">คำถาม</span>
            </h3>
            <p className="text-[13px] text-slate-500 dark:text-slate-400 font-semibold">
              จากคำถามสะสมทั้งหมด {history.length} ในฐานข้อมูล
            </p>
          </div>
          <span className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-500 flex items-center justify-center text-xl shrink-0"><i className="fa-solid fa-comments"></i></span>
        </div>

        {/* Period Switcher Card */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm flex flex-col justify-between col-span-2">
          <div>
            <span className="text-[15px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ฟิลเตอร์สลับช่วงเวลาบันทึกประวัติ</span>
            <p className="text-[15px] text-slate-500 dark:text-slate-400 font-semibold mt-1">เลือกช่วงเวลาเพื่อปรับการแสดงสถิติจำนวนคำถามและการแสดงตารางรายละเอียดด้านล่าง</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-4 lg:mt-0">
            <div className="flex items-center tuh-glass-3 p-1 rounded-2xl">
              {[
                { key: 'daily', label: 'รายวัน' },
                { key: 'weekly', label: 'รายสัปดาห์' },
                { key: 'monthly', label: 'รายเดือน' },
                { key: 'yearly', label: 'รายปี' },
                { key: 'all', label: 'ทั้งหมด' }
              ].map(p => (
                <button
                  key={p.key}
                  onClick={() => {
                    setHistoryPeriod(p.key);
                    setHistoryStartDate('');
                    setHistoryEndDate('');
                  }}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${(!historyStartDate && !historyEndDate && historyPeriod === p.key) ? 'bg-white dark:bg-tuh-purple/35 text-tuh-rose dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* TABLE CARD */}
      <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-extrabold flex items-center gap-2">
              <i className="fa-solid fa-clock-rotate-left text-tuh-rose"></i> ตารางรายการประวัติการตอบของบอท
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
              บันทึกรายการคำถาม-คำตอบ อ้างอิงตามระยะเวลาที่เลือก (ดาวน์โหลด CSV เพื่อส่งออกข้อมูลตามฟิลเตอร์ที่เลือก)
            </p>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={downloadCSV}
              disabled={filteredHistory.length === 0}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs shadow-sm hover:shadow"
            >
              <i className="fa-solid fa-file-csv"></i> ดาวน์โหลด CSV
            </button>
          </div>
        </div>

        {/* Sub-bar for history table filtering and sorting */}
        <div className="px-5 py-3.5 bg-slate-50/50 dark:bg-tuh-navy/10 border-b border-slate-100 dark:border-tuh-purple/10 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* Sort Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เรียงตามวัน:</span>
              <select
                value={historySortOrder}
                onChange={(e) => setHistorySortOrder(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              >
                <option value="desc">ใหม่ไปเก่า (ล่าสุด)</option>
                <option value="asc">เก่าไปใหม่</option>
              </select>
            </div>

            {/* Limit Selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">แสดงผลล่าสุด:</span>
              <select
                value={historyLimit}
                onChange={(e) => setHistoryLimit(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              >
                <option value="1000">1,000 รายการ</option>
                <option value="2000">2,000 รายการ</option>
                <option value="3000">3,000 รายการ</option>
                <option value="all">ทั้งหมด</option>
              </select>
            </div>

            {/* Start Date */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">เริ่มต้น:</span>
              <input
                type="date"
                value={historyStartDate}
                onChange={(e) => setHistoryStartDate(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              />
            </div>

            {/* End Date */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 whitespace-nowrap">สิ้นสุด:</span>
              <input
                type="date"
                value={historyEndDate}
                onChange={(e) => setHistoryEndDate(e.target.value)}
                className="tuh-glass-2 rounded-xl py-1.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white"
              />
            </div>

            {/* Clear Button */}
            {(historyStartDate || historyEndDate) && (
              <button
                onClick={() => {
                  setHistoryStartDate('');
                  setHistoryEndDate('');
                }}
                className="text-xs font-bold text-rose-500 hover:text-rose-600 transition"
              >
                ล้างค่า
              </button>
            )}
          </div>

          {/* Status Indicator */}
          {(historyStartDate || historyEndDate) && (
            <span className="bg-tuh-rose/10 text-tuh-rose border border-tuh-rose/20 px-3 py-1 rounded-full text-xs font-bold">
              ฟิลเตอร์แบบกำหนดช่วงเวลาเปิดใช้งานอยู่
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                <th className="px-6 py-4 w-44">เวลาที่ตอบ</th>
                <th className="px-6 py-4 w-64">คำถามจากผู้ใช้</th>
                <th className="px-6 py-4">คำตอบที่บอทตอบออกไป</th>
                <th className="px-6 py-4 w-44">โมเดล AI</th>
                <th className="px-6 py-4 w-32 text-center">Chunk ID</th>
                <th className="px-6 py-4 w-32 text-right">เวลาตอบสนอง</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
              {loadingHistory ? (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-slate-500 font-bold">
                    <div className="inline-block w-6 h-6 border-2 border-tuh-rose border-t-transparent rounded-full animate-spin mr-2"></div>
                    กำลังโหลดประวัติ...
                  </td>
                </tr>
              ) : filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-bold">
                    ไม่มีประวัติการตอบคำถามในช่วงเวลาที่เลือก
                  </td>
                </tr>
              ) : (
                (() => {
                  const sorted = [...filteredHistory].sort((a, b) => {
                    const dateA = parseTimestamp(a.timestamp);
                    const dateB = parseTimestamp(b.timestamp);
                    return historySortOrder === 'desc' ? dateB - dateA : dateA - dateB;
                  });

                  const limitVal = historyLimit === 'all' ? sorted.length : parseInt(historyLimit, 10);
                  const sliced = sorted.slice(0, limitVal);

                  return sliced.map((log) => {
                    const modelName = log.api_model || log.model || "";
                    const isFaq = modelName === "Direct FAQ" || modelName === "custom_faq" || !modelName;
                    return (
                      <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                        {/* Time */}
                        <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 align-top whitespace-nowrap">
                          <div className="font-bold text-slate-500 dark:text-slate-305">{log.timestamp.split(" ")[0]}</div>
                          <div className="text-[10px] mt-0.5">{log.timestamp.split(" ")[1] || ""}</div>
                        </td>

                        {/* Question */}
                        <td className="px-6 py-4 text-slate-800 dark:text-slate-100 align-top break-words max-w-xs font-bold">
                          {log.query}
                        </td>

                        {/* Answer */}
                        <td className="px-6 py-4 text-slate-600 dark:text-slate-300 align-top font-normal max-w-md">
                          <div className="max-h-64 overflow-y-auto text-xs whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-black/10 p-2.5 rounded-xl border border-slate-100 dark:border-white/5 font-semibold">
                            {log.answer}
                          </div>
                        </td>

                        {/* Model */}
                        <td className="px-6 py-4 align-top whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-extrabold ${isFaq
                            ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                            : modelName.includes("Ollama")
                              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            }`}>
                            <i className={isFaq ? "fa-solid fa-book" : "fa-solid fa-robot"}></i>
                            {modelName || "Direct FAQ"}
                          </span>
                        </td>

                        {/* Chunk ID */}
                        <td className="px-6 py-4 align-top text-center whitespace-nowrap">
                          {(!log.chunk_ids || log.chunk_ids.length === 0) ? (
                            <span className="text-slate-500 dark:text-slate-400 text-xs">-</span>
                          ) : (
                            <div className="flex flex-wrap gap-1 justify-center max-w-[120px]">
                              {log.chunk_ids.map(cid => {
                                const chunkInfo = chunksMap[String(cid)] || chunksMap[Number(cid)];
                                if (chunkInfo && chunkInfo.source) {
                                  const pdfUrl = `${API_URL}/api/documents/serve/${encodeURIComponent(chunkInfo.source)}${chunkInfo.page ? `#page=${chunkInfo.page}` : ''}`;
                                  return (
                                    <a
                                      key={cid}
                                      href={pdfUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="bg-sky-500/10 hover:bg-sky-500/20 text-sky-600 dark:text-sky-400 text-xs font-extrabold px-1.5 py-0.5 rounded cursor-pointer transition-colors"
                                      title={`เปิดดู ${chunkInfo.source} หน้า ${chunkInfo.page || 1}`}
                                    >
                                      #{cid}
                                    </a>
                                  );
                                }
                                return (
                                  <span key={cid} className="bg-sky-500/10 text-sky-600 dark:text-sky-400 text-xs font-extrabold px-1.5 py-0.5 rounded">
                                    #{cid}
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </td>

                        {/* Response Time */}
                        <td className="px-6 py-4 align-top text-right whitespace-nowrap text-slate-700 dark:text-slate-300 font-extrabold text-xs">
                          {isFaq ? (
                            <span className="text-slate-500 dark:text-slate-400 text-xs">0.0 วินาที</span>
                          ) : (
                            <span>{typeof log.response_time === 'number' ? log.response_time.toFixed(3) : log.response_time} วินาที</span>
                          )}
                        </td>
                      </tr>
                    );
                  });
                })()
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
