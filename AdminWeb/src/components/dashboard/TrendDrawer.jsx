/**
 * TrendDrawer — slide-out panel แสดง Q&A เบื้องหลังจุดที่ถูกคลิกบนกราฟแนวโน้มของหน้า Dashboard
 * แยกออกมาจาก DashboardPage.jsx เดิม (คืนค่า null ถ้าไม่มี
 * trendDrawer ที่จะแสดง เหมือนเงื่อนไข `{trendDrawer && (...)}` เดิม)
 */
export default function TrendDrawer({ trendDrawer, onClose, chunksMap, API_URL }) {
  if (!trendDrawer) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white dark:bg-tuh-navy shadow-2xl flex flex-col animate-slide-in-right">
        <div className={`px-6 py-5 border-b border-slate-100 dark:border-tuh-purple/10 flex items-center justify-between gap-3 ${trendDrawer.type === 'answered' ? 'bg-sky-500/5' : 'bg-rose-500/5'}`}>
          <div>
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black uppercase tracking-wider mb-1 ${trendDrawer.type === 'answered' ? 'bg-sky-500/15 text-sky-600 dark:text-sky-400' : 'bg-rose-500/15 text-rose-600 dark:text-rose-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${trendDrawer.type === 'answered' ? 'bg-sky-500' : 'bg-rose-500'}`}></span>
              {trendDrawer.type === 'answered' ? 'ตอบสำเร็จ' : 'ตอบไม่ได้'}
            </span>
            <h3 className="text-base font-extrabold text-tuh-navy dark:text-white">
              วันที่ {trendDrawer.dateLabel} · {trendDrawer.items.length} รายการ
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center text-slate-400 hover:text-tuh-rose hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-5 space-y-4">
          {trendDrawer.items.length === 0 ? (
            <div className="py-16 text-center text-slate-400 dark:text-slate-500 font-bold space-y-2">
              <div className="text-4xl">
                <i className={trendDrawer.type === 'answered' ? "fa-regular fa-comment-dots" : "fa-regular fa-circle-check"}></i>
              </div>
              <p>ไม่มีข้อมูลในวันนี้</p>
            </div>
          ) : trendDrawer.type === 'answered' ? (
            trendDrawer.items.map((log, idx) => (
              <div key={log.id || idx} className="p-4 rounded-2xl bg-slate-50/70 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">{log.timestamp}</span>
                </div>
                <p className="text-sm font-extrabold text-tuh-navy dark:text-white mb-2">{log.query}</p>
                <div className="text-xs whitespace-pre-wrap leading-relaxed bg-white dark:bg-black/20 p-3 rounded-xl border border-slate-100 dark:border-white/5 text-slate-600 dark:text-slate-300 font-semibold max-h-40 overflow-y-auto">
                  {log.answer}
                </div>
                {log.chunk_ids && log.chunk_ids.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2.5">
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
              </div>
            ))
          ) : (
            trendDrawer.items.map((u, idx) => (
              <div key={u.id || idx} className="p-4 rounded-2xl bg-slate-50/70 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">{u.timestamp}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black ${u.status === 'Pending' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'}`}>
                    {u.status === 'Pending' ? 'รอสอนบอท' : (u.status || 'Resolved')}
                  </span>
                </div>
                <p className="text-sm font-extrabold text-tuh-navy dark:text-white">{u.query}</p>
                {u.count > 1 && (
                  <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 mt-1.5">ถูกถามซ้ำ {u.count} ครั้ง</p>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
