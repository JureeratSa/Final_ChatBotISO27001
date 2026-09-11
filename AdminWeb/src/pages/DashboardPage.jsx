import { useAdminContext } from '../context/AdminContext';

/**
 * DashboardPage — แท็บ "ภาพรวม" หน้าแรกหลัง login (สรุปสถิติ, กราฟแนวโน้ม, comment ล่าสุด)
 * แยกออกมาจาก App.jsx เดิม (เคยเป็น IIFE ยาว ~580 บรรทัดฝังอยู่ใน return ของ App())
 */
export default function DashboardPage() {
  const {
  API_URL,
  activeTab,
  analysisLoading,
  analysisResult,
  announcements,
  chunksMap,
  currentUnanswered,
  documents,
  faqAnswer,
  feedback,
  handleSubmitFaq,
  history,
  isDarkMode,
  parseTimestamp,
  pendingUnansweredCount,
  setActiveTab,
  setCurrentUnanswered,
  setFaqAnswer,
  setShowFaqModal,
  setTrendDrawer,
  settings,
  showFaqModal,
  showSuccess,
  stats,
  trendDrawer,
  unanswered,
  } = useAdminContext();

            // Helper function to build the Line Chart trend data strictly from real history/unanswered logs
            const getTrendData = () => {
              const dates = [];
              const answeredCounts = [];
              const unansweredCounts = [];
              const answeredItems = [];
              const unansweredItems = [];
              for (let i = 6; i >= 0; i--) {
                const d = new Date();
                d.setDate(d.getDate() - i);
                const dateStr = d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short' });
                dates.push(dateStr);

                const dateKey = d.toDateString();
                const histOnDay = history.filter(h => parseTimestamp(h.timestamp).toDateString() === dateKey);
                const unansOnDay = unanswered.filter(u => parseTimestamp(u.timestamp).toDateString() === dateKey);

                answeredCounts.push(histOnDay.length);
                unansweredCounts.push(unansOnDay.length);
                answeredItems.push(histOnDay);
                unansweredItems.push(unansOnDay);
              }
              return { dates, answeredCounts, unansweredCounts, answeredItems, unansweredItems };
            };

            const trend = getTrendData();
            
            // Doughnut Chart percentages calculation — นับเฉพาะคำตอบที่มีคนกด like/dislike จริงเท่านั้น
            // (ไม่รวมคำถามที่ไม่มีใครกด feedback เลย เพื่อให้ตรงกับตัวเลข CSAT กลางวงและ subtitle ของการ์ด)
            const likeVal = stats.likes || 0;
            const dislikeVal = stats.dislikes || 0;
            const doughnutTotal = likeVal + dislikeVal;
            const likePct = doughnutTotal > 0 ? Math.round((likeVal / doughnutTotal) * 100) : 0;
            const dislikePct = doughnutTotal > 0 ? 100 - likePct : 0;

            // Render SVG Line Chart points
            const maxVal = Math.max(...trend.answeredCounts, ...trend.unansweredCounts, 10);
            const padding = 35;
            const chartW = 500;
            const chartH = 180;
            
            const getCoordinates = (counts) => {
              return counts.map((val, idx) => {
                const x = padding + (idx * (chartW - padding * 2) / 6);
                const y = chartH - padding - (val * (chartH - padding * 2) / maxVal);
                return { x, y };
              });
            };

            const ansCoords = getCoordinates(trend.answeredCounts);
            const unansCoords = getCoordinates(trend.unansweredCounts);

            const ansPath = ansCoords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');
            const unansPath = unansCoords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');

            const ansAreaPath = `${ansPath} L ${ansCoords[ansCoords.length - 1].x} ${chartH - padding} L ${ansCoords[0].x} ${chartH - padding} Z`;
            const unansAreaPath = `${unansPath} L ${unansCoords[unansCoords.length - 1].x} ${chartH - padding} L ${unansCoords[0].x} ${chartH - padding} Z`;

            // Active announcements count
            const activeAnns = announcements.filter(ann => {
              const now = new Date();
              return now >= new Date(ann.start_date) && now <= new Date(ann.end_date);
            });

            // Pending unanswered questions (limit to 5)
            const pendingUnanswered = unanswered.filter(u => u.status === 'Pending').slice(0, 5);

            return (
              <>
              <div className="space-y-6 animate-slide-in">

                {/* ส่วนที่ 1: การ์ดสรุปตัวเลขสำคัญ (Key Metric Cards) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                  
                  {/* Card 1: คำถามที่บอทตอบไม่ได้ */}
                  <div 
                    onClick={() => setActiveTab('logs')}
                    className="cursor-pointer group relative overflow-hidden rounded-3xl p-5 bg-gradient-to-br from-rose-500 to-pink-600 text-white shadow-md hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
                  >
                    <div className="absolute right-3 top-3 opacity-20 text-5xl group-hover:scale-110 transition-transform duration-300">
                      <i className="fa-solid fa-circle-question"></i>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 uppercase tracking-wider mb-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-yellow-300 animate-ping"></span>
                      Action Required
                    </span>
                    <h4 className="text-sm font-extrabold opacity-95">คำถามที่รอสอนบอท</h4>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-black">{pendingUnansweredCount}</span>
                      <span className="text-xs font-bold opacity-80">คำถามค้างตอบ</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/15 flex items-center justify-between text-xs font-bold opacity-90">
                      <span>คลิกเพื่อเข้าไปตอบกลับ</span>
                      <i className="fa-solid fa-arrow-right"></i>
                    </div>
                  </div>

                  {/* Card 2: ความพึงพอใจเฉลี่ย */}
                  <div 
                    onClick={() => setActiveTab('satisfaction')}
                    className="cursor-pointer group relative overflow-hidden rounded-3xl p-5 bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-md hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
                  >
                    <div className="absolute right-3 top-3 opacity-20 text-5xl group-hover:scale-110 transition-transform duration-300">
                      <i className="fa-solid fa-face-smile"></i>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                      CSAT Score
                    </span>
                    <h4 className="text-sm font-extrabold opacity-95">ความพึงพอใจเฉลี่ย</h4>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-black">
                        {stats.likes + stats.dislikes > 0 ? Math.round((stats.likes / (stats.likes + stats.dislikes)) * 100) : 100}%
                      </span>
                      <span className="text-xs font-bold opacity-80">จากประเมิน {stats.likes + stats.dislikes} ครั้ง</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/15 flex items-center justify-between text-xs font-bold opacity-90">
                      <span>ดูรายละเอียดสถิติ</span>
                      <i className="fa-solid fa-arrow-right"></i>
                    </div>
                  </div>

                  {/* Card 3: จำนวนการตอบของบอท */}
                  <div 
                    onClick={() => setActiveTab('history')}
                    className="cursor-pointer group relative overflow-hidden rounded-3xl p-5 bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-md hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
                  >
                    <div className="absolute right-3 top-3 opacity-20 text-5xl group-hover:scale-110 transition-transform duration-300">
                      <i className="fa-solid fa-clock-rotate-left"></i>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                      Bot Responses
                    </span>
                    <h4 className="text-sm font-extrabold opacity-95">ยอดการตอบของบอท</h4>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-black">{stats.total_queries}</span>
                      <span className="text-xs font-bold opacity-80">ถามตอบสะสม ({stats.queries_today} วันนี้)</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/15 flex items-center justify-between text-xs font-bold opacity-90">
                      <span>ประวัติความเร็วการตอบ</span>
                      <i className="fa-solid fa-arrow-right"></i>
                    </div>
                  </div>

                  {/* Card 4: จำนวนฐานข้อมูลคลังความรู้ */}
                  <div 
                    onClick={() => setActiveTab('documents')}
                    className="cursor-pointer group relative overflow-hidden rounded-3xl p-5 bg-gradient-to-br from-purple-500 to-fuchsia-600 text-white shadow-md hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
                  >
                    <div className="absolute right-3 top-3 opacity-20 text-5xl group-hover:scale-110 transition-transform duration-300">
                      <i className="fa-solid fa-file-pdf"></i>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                      Knowledge Bank
                    </span>
                    <h4 className="text-sm font-extrabold opacity-95">ฐานข้อมูลเข้าระบบ RAG</h4>
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-3xl font-black">{stats.total_documents} PDF</span>
                      <span className="text-xs font-bold opacity-80 font-black">/ {settings.predefined_faqs?.length || 0} FAQs</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/15 flex items-center justify-between text-xs font-bold opacity-90">
                      <span>จัดการคลังเอกสาร</span>
                      <i className="fa-solid fa-arrow-right"></i>
                    </div>
                  </div>

                </div>

                {/* ส่วนที่ 2: กราฟแสดงสถิติและแนวโน้ม (Charts & Trends) */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Line Chart: ประวัติการตอบและแนวโน้ม 7 วันย้อนหลัง */}
                  <div className="lg:col-span-2 tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10">
                    <div className="flex items-center justify-between border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
                      <div>
                        <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                          <i className="fa-solid fa-chart-line text-tuh-pink"></i> แนวโน้มถามตอบของผู้ใช้ย้อนหลัง 7 วัน
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">เปรียบเทียบปริมาณคำถามที่บอทตอบได้สำเร็จ vs คำถามค้างตอบ</p>
                      </div>
                      <div className="flex items-center gap-4 text-xs font-bold">
                        <span className="flex items-center gap-1.5 text-sky-500">
                          <span className="w-3 h-3 rounded bg-sky-500"></span> ตอบสำเร็จ
                        </span>
                        <span className="flex items-center gap-1.5 text-rose-500">
                          <span className="w-3 h-3 rounded bg-rose-500"></span> ตอบไม่ได้
                        </span>
                      </div>
                    </div>

                    <div className="relative w-full h-[200px] flex items-center justify-center">
                      <svg className="w-full h-full overflow-visible" viewBox={`0 0 ${chartW} ${chartH}`}>
                        <defs>
                          <linearGradient id="ansGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.0" />
                          </linearGradient>
                          <linearGradient id="unansGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Grid lines */}
                        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
                          const y = padding + ratio * (chartH - padding * 2);
                          const gridVal = Math.round(maxVal - ratio * maxVal);
                          return (
                            <g key={idx}>
                              <line 
                                x1={padding} 
                                y1={y} 
                                x2={chartW - padding} 
                                y2={y} 
                                stroke={isDarkMode ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)"} 
                                strokeDasharray="3 3" 
                              />
                              <text 
                                x={padding - 8} 
                                y={y + 4} 
                                fill={isDarkMode ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.4)"} 
                                fontSize="9" 
                                fontWeight="bold" 
                                textAnchor="end"
                              >
                                {gridVal}
                              </text>
                            </g>
                          );
                        })}

                        {/* Gradient Area under paths */}
                        <path d={ansAreaPath} fill="url(#ansGradient)" />
                        <path d={unansAreaPath} fill="url(#unansGradient)" />

                        {/* Strokes */}
                        <path d={ansPath} fill="none" stroke="#0ea5e9" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                        <path d={unansPath} fill="none" stroke="#f43f5e" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

                        {/* Coordinate points and tooltip labels — click a point to see that day's Q&A in the slide-out panel */}
                        {ansCoords.map((c, i) => (
                          <g
                            key={`ans-pt-${i}`}
                            className="group/pt cursor-pointer"
                            onClick={() => setTrendDrawer({
                              dateLabel: trend.dates[i],
                              type: 'answered',
                              items: trend.answeredItems[i],
                            })}
                          >
                            <circle cx={c.x} cy={c.y} r="7" fill="transparent" />
                            <circle cx={c.x} cy={c.y} r="4" fill="#ffffff" stroke="#0ea5e9" strokeWidth="2.5" className="hover:scale-150 transition-all duration-200" style={{ transformBox: 'fill-box', transformOrigin: 'center' }} />
                            <text x={c.x} y={c.y - 8} fill={isDarkMode ? "#ffffff" : "#0f172a"} fontSize="9" fontWeight="black" textAnchor="middle" className="opacity-0 group-hover/pt:opacity-100 bg-slate-900 transition-opacity pointer-events-none">
                              {trend.answeredCounts[i]}
                            </text>
                          </g>
                        ))}

                        {unansCoords.map((c, i) => (
                          <g
                            key={`unans-pt-${i}`}
                            className="group/pt cursor-pointer"
                            onClick={() => setTrendDrawer({
                              dateLabel: trend.dates[i],
                              type: 'unanswered',
                              items: trend.unansweredItems[i],
                            })}
                          >
                            <circle cx={c.x} cy={c.y} r="7" fill="transparent" />
                            <circle cx={c.x} cy={c.y} r="4" fill="#ffffff" stroke="#f43f5e" strokeWidth="2.5" className="hover:scale-150 transition-all duration-200" style={{ transformBox: 'fill-box', transformOrigin: 'center' }} />
                            <text x={c.x} y={c.y - 8} fill={isDarkMode ? "#ffffff" : "#0f172a"} fontSize="9" fontWeight="black" textAnchor="middle" className="opacity-0 group-hover/pt:opacity-100 bg-slate-900 transition-opacity pointer-events-none">
                              {trend.unansweredCounts[i]}
                            </text>
                          </g>
                        ))}

                        {/* X Axis Labels */}
                        {trend.dates.map((d, idx) => {
                          const x = padding + (idx * (chartW - padding * 2) / 6);
                          return (
                            <text 
                              key={idx} 
                              x={x} 
                              y={chartH - 8} 
                              fill={isDarkMode ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.5)"} 
                              fontSize="9" 
                              fontWeight="bold" 
                              textAnchor="middle"
                            >
                              {d}
                            </text>
                          );
                        })}
                      </svg>
                    </div>
                  </div>

                  {/* Doughnut Chart: อัตราความพึงพอใจการให้บริการ */}
                  <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
                    <div className="border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
                      <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                        <i className="fa-solid fa-face-smile text-tuh-pink"></i> สัดส่วนความพึงพอใจ CSAT
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">แบ่งตามการกดยอมรับคำตอบของผู้ใช้งานแชทบอท</p>
                    </div>

                    <div className="flex-1 flex items-center justify-center gap-6">
                      {/* SVG Doughnut */}
                      <div className="relative w-32 h-32 flex items-center justify-center">
                        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                          {/* Segment 1: Good (Green) */}
                          <circle 
                            cx="18" 
                            cy="18" 
                            r="15.915" 
                            fill="transparent" 
                            stroke="#10b981" 
                            strokeWidth="3.2" 
                            strokeDasharray={`${likePct} ${100 - likePct}`}
                            strokeDashoffset="0"
                          />
                          {/* Segment 2: Needs Improvement (Red) */}
                          <circle
                            cx="18"
                            cy="18"
                            r="15.915"
                            fill="transparent"
                            stroke="#ef4444"
                            strokeWidth="3.2"
                            strokeDasharray={`${dislikePct} ${100 - dislikePct}`}
                            strokeDashoffset={`-${likePct}`}
                          />
                        </svg>
                        <div className="absolute flex flex-col items-center justify-center text-center">
                          <span className="text-xs font-black text-slate-400 uppercase tracking-widest">CSAT</span>
                          <span className="text-xl font-black text-emerald-500 dark:text-emerald-400">
                            {likePct}%
                          </span>
                        </div>
                      </div>

                      {/* Legend details */}
                      <div className="space-y-2 text-xs font-bold text-slate-600 dark:text-slate-300">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                          <span>ดีมาก: {likePct}%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                          <span>ปรับปรุง: {dislikePct}%</span>
                        </div>
                        <div className="text-[11px] font-medium text-slate-400 dark:text-slate-500 pt-1">
                          จาก {doughnutTotal} คำตอบที่มีคนกด feedback
                        </div>
                      </div>
                    </div>
                  </div>

                </div>

                {/* ส่วนที่ 3: รายการอัปเดตและงานที่ต้องทำ (Recent Activity & Tasks) */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Left Table: ตารางรายการคำถามที่บอทตอบไม่ได้ */}
                  <div className="lg:col-span-2 tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
                        <div>
                          <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                            <i className="fa-solid fa-clipboard-list text-tuh-pink"></i> คำถามที่บอทงงล่าสุด (Action Needed)
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">แอดมินสามารถกดเพื่อตอบคำถามและเพิ่มเข้าระบบ FAQs ได้ทันที</p>
                        </div>
                        <span className="px-2.5 py-1 text-xs font-black rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
                          {pendingUnanswered.length} รายการล่าสุด
                        </span>
                      </div>

                      {pendingUnanswered.length === 0 ? (
                        <div className="py-12 text-center text-slate-400 dark:text-slate-500 font-bold space-y-2">
                          <div className="text-4xl"><i className="fa-regular fa-face-laugh-beam"></i></div>
                          <p>ยอดเยี่ยม! ไม่มีคำถามที่บอทตอบไม่ได้ค้างอยู่เลย</p>
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead>
                              <tr className="border-b border-slate-100 dark:border-tuh-purple/10 text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">
                                <th className="pb-3 pl-2">ข้อความคำถามจากผู้ใช้</th>
                                <th className="pb-3 text-center">ถามซ้ำ</th>
                                <th className="pb-3">วันที่ถาม</th>
                                <th className="pb-3 text-right">การจัดการ</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/5 font-semibold text-tuh-navy dark:text-slate-100">
                              {pendingUnanswered.map((u, idx) => (
                                <tr key={u.id || idx} className="hover:bg-slate-50/50 dark:hover:bg-tuh-purple/5 transition-all">
                                  <td className="py-3.5 pl-2 font-bold max-w-xs truncate pr-4">{u.query}</td>
                                  <td className="py-3.5 text-center">
                                    <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-tuh-purple/20 text-slate-600 dark:text-slate-300 font-black">
                                      {u.count}
                                    </span>
                                  </td>
                                  <td className="py-3.5 text-slate-400 dark:text-slate-400 font-bold">
                                    {new Date(u.timestamp).toLocaleDateString('th-TH', { 
                                      day: 'numeric', 
                                      month: 'short', 
                                      hour: '2-digit', 
                                      minute: '2-digit' 
                                    })}
                                  </td>
                                  <td className="py-3.5 text-right pr-2">
                                    <button
                                      onClick={() => {
                                        setCurrentUnanswered(u);
                                        setFaqAnswer('');
                                        setShowFaqModal(true);
                                      }}
                                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-tuh-pink/15 hover:bg-tuh-pink/25 text-tuh-rose text-xs font-black transition active:scale-[0.97]"
                                    >
                                      <i className="fa-solid fa-plus-circle"></i> เพิ่มใน FAQs
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: รายการประกาศล่าสุดที่ Active */}
                  <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm border border-slate-100 dark:border-tuh-purple/10 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
                        <div>
                          <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                            <i className="fa-solid fa-bullhorn text-tuh-pink"></i> ประกาศระบบที่ทำงานอยู่
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">ประกาศประชาสัมพันธ์แชทบอทล่าสุด</p>
                        </div>
                        <span className="px-2.5 py-1 text-xs font-black rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                          {activeAnns.length} ทำงานอยู่
                        </span>
                      </div>

                      {activeAnns.length === 0 ? (
                        <div className="py-12 text-center text-slate-400 dark:text-slate-500 font-bold space-y-2">
                          <div className="text-4xl"><i className="fa-solid fa-volume-xmark"></i></div>
                          <p>ไม่มีประกาศระบบที่กำลัง Active ในช่วงเวลานี้</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {activeAnns.slice(0, 3).map((ann, idx) => (
                            <div 
                              key={ann.id || idx}
                              className="p-4 rounded-2xl bg-slate-50/50 dark:bg-tuh-purple/5 border border-slate-100/50 dark:border-tuh-purple/10 hover:border-tuh-rose/25 transition-all"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <h4 className="font-extrabold text-sm text-tuh-navy dark:text-white truncate">{ann.title}</h4>
                                <span className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-black bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                                  Active
                                </span>
                              </div>
                              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{ann.content}</p>
                              <div className="mt-2.5 flex items-center justify-between text-[10px] font-bold text-slate-400 dark:text-slate-500 border-t border-slate-100/60 dark:border-tuh-purple/5 pt-2">
                                <span><i className="fa-regular fa-calendar-days"></i> วันที่เผยแพร่:</span>
                                <span>{new Date(ann.start_date).toLocaleDateString('th-TH', { day: 'numeric', month: 'short' })} - {new Date(ann.end_date).toLocaleDateString('th-TH', { day: 'numeric', month: 'short' })}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <button 
                      onClick={() => setActiveTab('announcements')}
                      className="w-full mt-4 py-2.5 px-4 rounded-xl border border-dashed border-slate-200 dark:border-tuh-purple/20 hover:border-tuh-rose/50 hover:text-tuh-rose text-xs font-black transition-all flex items-center justify-center gap-2 text-slate-500 dark:text-slate-400"
                    >
                      <i className="fa-solid fa-list"></i> จัดการประกาศทั้งหมด
                    </button>
                  </div>

                </div>

              </div>

              {/* Slide-out panel: Q&A behind the clicked point on the trend chart */}
              {trendDrawer && (
                <>
                  <div
                    className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
                    onClick={() => setTrendDrawer(null)}
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
                        onClick={() => setTrendDrawer(null)}
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
              )}

              {/* MODAL: ANSWER FAQ MODAL — เปิดจากปุ่ม "เพิ่มใน FAQs" ของตารางคำถามที่บอทงงล่าสุดด้านบน */}
              {showFaqModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                  <div className="w-full max-w-lg tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
                    <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
                      <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                        <i className="fa-solid fa-feather text-tuh-rose"></i> ลงทะเบียนคำตอบตอบกลับ FAQ
                      </h3>
                      <button
                        onClick={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
                        className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
                      >
                        <i className="fa-solid fa-xmark text-lg"></i>
                      </button>
                    </div>

                    <form onSubmit={handleSubmitFaq} className="p-6 space-y-4">
                      {currentUnanswered.query && (
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามจากผู้ใช้</label>
                          <div className="p-4 tuh-glass-2 rounded-2xl font-bold">
                            {currentUnanswered.query}
                          </div>
                        </div>
                      )}

                      {!currentUnanswered.query && (
                        <div>
                          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามแอดมินตั้งขึ้น</label>
                          <input
                            type="text"
                            required
                            placeholder="พิมพ์ประโยคคำถาม..."
                            value={currentUnanswered.query || ''}
                            onChange={(e) => setCurrentUnanswered({ ...currentUnanswered, query: e.target.value })}
                            className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                          />
                        </div>
                      )}

                      {/* AI Query Analysis Recommendations */}
                      {(analysisLoading || analysisResult) && (
                        <div className="p-4 rounded-2xl border border-dashed border-tuh-purple/20 bg-slate-50 dark:bg-[#100220]/25 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                              <i className="fa-solid fa-wand-magic-sparkles text-tuh-rose animate-pulse"></i>
                              วิเคราะห์ประโยคและคำค้นหาแนะนำโดย AI
                            </span>
                            {analysisLoading && (
                              <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
                                <i className="fa-solid fa-spinner animate-spin text-[10px]"></i> กำลังวิเคราะห์...
                              </span>
                            )}
                          </div>

                          {analysisResult && (
                            <div className="space-y-2">
                              {analysisResult.is_valid_query === false ? (
                                <div className="text-xs font-semibold text-rose-500 dark:text-rose-455 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
                                  ⚠️ AI ประเมินว่าเป็นข้อความขยะหรือคำทักทายทั่วไป (ไม่ใช่คำถามเกี่ยวกับสวัสดิการ)
                                </div>
                              ) : (
                                <div className="space-y-2">
                                  <div className="flex flex-wrap gap-1.5">
                                    {analysisResult.suggested_keywords && analysisResult.suggested_keywords.map((kw, i) => (
                                      <button
                                        key={i}
                                        type="button"
                                        onClick={() => {
                                          navigator.clipboard.writeText(kw);
                                          showSuccess(`คัดลอกคำว่า "${kw}" แล้ว`);
                                        }}
                                        className="px-2.5 py-1 text-xs font-bold rounded-lg bg-tuh-rose/10 text-tuh-rose hover:bg-tuh-rose/20 transition active:scale-95 flex items-center gap-1"
                                      >
                                        {kw}
                                        <i className="fa-regular fa-copy text-[10px] opacity-60"></i>
                                      </button>
                                    ))}
                                  </div>
                                  <div className="text-[10px] text-slate-500 dark:text-slate-450 font-semibold">
                                    💡 คลิกที่คำสำคัญแนะนำด้านบนเพื่อคัดลอกและนำไปใช้ในการแต่งประโยค FAQ เพื่อการค้นหาที่แม่นยำขึ้น
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เขียนคู่มือคำตอบ (บอทจะตอบประโยคนี้ตรงๆ ทันที)</label>
                        <textarea
                          rows="4"
                          required
                          placeholder="เขียนคำตอบที่สั้น กระชับ ตรงประเด็นสำหรับคำถามนี้..."
                          value={faqAnswer}
                          onChange={(e) => setFaqAnswer(e.target.value)}
                          className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm leading-relaxed"
                        ></textarea>
                      </div>

                      <div className="flex justify-end gap-3 pt-2">
                        <button
                          type="button"
                          onClick={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
                          className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                        >
                          ยกเลิก
                        </button>
                        <button
                          type="submit"
                          className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                        >
                          <i className="fa-solid fa-save mr-1.5"></i> ลงทะเบียนคำตอบสำเร็จ
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
              </>
            );
}
