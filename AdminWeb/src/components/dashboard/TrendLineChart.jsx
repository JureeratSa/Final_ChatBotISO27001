/**
 * TrendLineChart — กราฟเส้น SVG แสดงแนวโน้มถามตอบย้อนหลัง 7 วัน (ตอบสำเร็จ vs ตอบไม่ได้)
 * ในหน้า Dashboard คลิกจุดบนกราฟเพื่อเปิด TrendDrawer ดู Q&A ของวันนั้น
 * แยกออกมาจาก DashboardPage.jsx เดิม
 *
 * getTrendData()/getCoordinates()/อัลกอริทึมหลีกเลี่ยง marker ชนกัน ยังคงเป็น local helper
 * ภายใน component นี้ตามแผน (ไม่ยกเป็น utility ภายนอก) พร้อม comment ภาษาไทยเดิมทุกคำ
 */
export default function TrendLineChart({ history, unanswered, parseTimestamp, isDarkMode, onPointClick }) {
  // Helper function to build the Line Chart trend data strictly from real history/unanswered logs
  const getTrendData = () => {
    // history (ChatHistory) เก็บทุกการสนทนาโดยไม่สนว่าตอบได้จริงหรือไม่ ในขณะที่ unanswered (UnansweredQuery)
    // เก็บเฉพาะคำถามที่ backend ตัดสินแล้วว่า "ตอบไม่ได้" (ดู Backend/app/routers/chat.py ~163-173)
    // ทำให้ query เดียวกันโผล่ทั้งฝั่ง "ตอบสำเร็จ" และ "ตอบไม่ได้" พร้อมกัน — ต้องกรอง history ที่ query
    // ตรงกับรายการใน unanswered ออกก่อนนับ เพื่อไม่ให้นับ/แสดงซ้ำในการ์ด "ตอบสำเร็จ"
    // ผูก key กับ "วันที่ + query" ไม่ใช่ query เฉยๆ เพราะคำถามเดียวกันอาจตอบสำเร็จวันหนึ่ง
    // แต่ตอบไม่ได้อีกวันหนึ่งก็ได้ — ถ้า exclude ด้วย query เพียวๆ (ไม่ผูกวัน) วันที่ตอบสำเร็จ
    // จริงจะถูกตัดออกจากกราฟไปด้วยอย่างผิดๆ เพราะคำถามเดียวกันไปโผล่ unanswered วันอื่น
    // สร้าง Set ของ "วันที่|query" ที่ normalize แล้ว (trim + lowercase) ไว้ล่วงหน้าครั้งเดียว
    // นอก loop เพื่อ performance เพราะ history/unanswered อาจมีหลายพันรายการ
    const unansweredDayQuerySet = new Set(
      unanswered.map(u => `${parseTimestamp(u.timestamp).toDateString()}|${(u.query || '').trim().toLowerCase()}`)
    );

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
      const histOnDay = history.filter(h =>
        parseTimestamp(h.timestamp).toDateString() === dateKey &&
        !unansweredDayQuerySet.has(`${dateKey}|${(h.query || '').trim().toLowerCase()}`)
      );
      const unansOnDay = unanswered.filter(u => parseTimestamp(u.timestamp).toDateString() === dateKey);

      answeredCounts.push(histOnDay.length);
      unansweredCounts.push(unansOnDay.length);
      answeredItems.push(histOnDay);
      unansweredItems.push(unansOnDay);
    }
    return { dates, answeredCounts, unansweredCounts, answeredItems, unansweredItems };
  };

  const trend = getTrendData();

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

  // เมื่อ "ตอบสำเร็จ" กับ "ตอบไม่ได้" ของวันเดียวกันมีจำนวนเท่ากัน ansCoords[i] กับ unansCoords[i]
  // จะคำนวณออกมาเป็นพิกัดเดียวกันเป๊ะ (มาจาก getCoordinates() function เดียวกัน) ทำให้ marker วงกลม/hit-area
  // ของทั้งสองเส้นไปวาดซ้อนทับกันพอดี — เพราะกลุ่ม <g> ของ "ตอบไม่ได้" render หลังใน DOM จึงอยู่บนสุดเสมอ
  // เวลาซ้อนกัน บังไม่ให้คลิกเปิด drawer "ตอบสำเร็จ" ของวันนั้นได้เลย จึงต้อง offset ตำแหน่ง marker
  // (วงกลม/hit-area/label ตัวเลข) ออกจากกันเล็กน้อยในแนวนอนเฉพาะตอนจุดชนกันเท่านั้น ส่วน path เส้น/พื้นที่
  // กราฟด้านบน (ansPath/unansPath/ansAreaPath/unansAreaPath) ยังคำนวณจาก ansCoords/unansCoords ดิบเหมือนเดิม
  // ไม่แตะต้อง เพื่อให้กราฟยังวาดตามค่าจริงแม่นยำ ไม่กระทบความถูกต้องของข้อมูล
  const MARKER_OFFSET = 4; // px ที่จะขยับ marker ออกจากกันเมื่อจุดชนกัน
  const COLLISION_THRESHOLD = 5; // px ถือว่า "ชนกัน" ถ้าห่างกันน้อยกว่านี้ทั้งแกน x และ y
  const ansMarkerCoords = ansCoords.map((c, i) => {
    const u = unansCoords[i];
    const isColliding = Math.abs(c.x - u.x) < COLLISION_THRESHOLD && Math.abs(c.y - u.y) < COLLISION_THRESHOLD;
    return isColliding ? { x: c.x - MARKER_OFFSET, y: c.y } : c;
  });
  const unansMarkerCoords = unansCoords.map((c, i) => {
    const a = ansCoords[i];
    const isColliding = Math.abs(c.x - a.x) < COLLISION_THRESHOLD && Math.abs(c.y - a.y) < COLLISION_THRESHOLD;
    return isColliding ? { x: c.x + MARKER_OFFSET, y: c.y } : c;
  });

  return (
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

          {/* Coordinate points and tooltip labels — click a point to see that day's Q&A in the slide-out panel
              ใช้ ansMarkerCoords/unansMarkerCoords (ไม่ใช่ ansCoords/unansCoords ดิบ) เพื่อให้จุดที่ชนกันพอดี
              ถูกขยับแยกออกจากกัน คลิกเปิด drawer ของแต่ละเส้นได้อิสระ ไม่บังกัน */}
          {ansMarkerCoords.map((c, i) => (
            <g
              key={`ans-pt-${i}`}
              className="group/pt cursor-pointer"
              onClick={() => onPointClick({
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

          {unansMarkerCoords.map((c, i) => (
            <g
              key={`unans-pt-${i}`}
              className="group/pt cursor-pointer"
              onClick={() => onPointClick({
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
  );
}
