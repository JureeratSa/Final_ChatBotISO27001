import { useAdminContext } from '../context/AdminContext';

/**
 * SatisfactionPage — แท็บ "สถิติความพึงพอใจ" สรุปอัตราไลก์/ดิสไลก์ ดาวประเมิน และ
 * ความคิดเห็นแยกตามช่วงเวลา — แยกออกมาจาก App.jsx เดิม
 */
export default function SatisfactionPage() {
  const {
    getSatisfactionStatsByPeriod,
    satPeriod,
    setSatPeriod,
  } = useAdminContext();

  const statsObj = getSatisfactionStatsByPeriod(satPeriod);

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Timeframe Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 tuh-glass-1 p-5 rounded-3xl shadow-sm">
        <div>
          <h3 className="text-lg font-extrabold flex items-center gap-2">
            <i className="fa-solid fa-face-smile text-emerald-500"></i> สถิติความพึงพอใจย้อนหลัง
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
            เลือกช่วงเวลาเพื่อดูสถิติอัตราไลก์/ดิสไลก์ ข้อเสนอแนะ และสถิติแยกตามหมวดหมู่คำถาม
          </p>
        </div>

        {/* Period Switcher Buttons */}
        <div className="flex items-center tuh-glass-3 p-1 rounded-2xl">
          {[
            { key: 'daily', label: 'รายวัน' },
            { key: 'weekly', label: 'รายสัปดาห์' },
            { key: 'monthly', label: 'รายเดือน' },
            { key: 'yearly', label: 'รายปี' }
          ].map(p => (
            <button
              key={p.key}
              onClick={() => setSatPeriod(p.key)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${satPeriod === p.key ? 'bg-white dark:bg-tuh-purple/35 text-tuh-rose dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid: 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Satisfaction rate */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">พึงพอใจการตอบคำถาม</span>
            <span className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-sm"><i className="fa-solid fa-circle-check"></i></span>
          </div>
          <h3 className={`text-3xl font-black tracking-tight ${statsObj.satRate >= 80 ? 'text-emerald-500' : statsObj.satRate >= 50 ? 'text-amber-500' : 'text-rose-500'}`}>
            {statsObj.satRate}%
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">อัตราความพึงพอใจคำตอบรอบนี้</p>
        </div>

        {/* Likes count */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ถูกใจคำตอบ (Likes)</span>
            <span className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-up"></i></span>
          </div>
          <h3 className="text-3xl font-black tracking-tight text-teal-500">{statsObj.totalLikes}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนที่กดถูกใจคำตอบบอท</p>
        </div>

        {/* Dislikes count */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ไม่ถูกใจคำตอบ (Dislikes)</span>
            <span className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-down"></i></span>
          </div>
          <h3 className="text-3xl font-black tracking-tight text-rose-500">{statsObj.totalDislikes}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนที่กดไม่ถูกใจคำตอบบอท</p>
        </div>

        {/* Total Feedbacks */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">การประเมินคำตอบทั้งหมด</span>
            <span className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-sm"><i className="fa-solid fa-comments"></i></span>
          </div>
          <h3 className="text-3xl font-black tracking-tight text-indigo-500">{statsObj.totalVotes}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนโหวตคำตอบบอททั้งหมด</p>
        </div>
      </div>

      {/* Grid: Likes vs Dislikes progress AND Star Ratings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Progress bar of Likes vs Dislikes */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-extrabold mb-4 flex items-center gap-2">
              <i className="fa-solid fa-thumbs-up text-teal-500"></i> สัดส่วนความพึงพอใจต่อคำตอบของแชทบอท
            </h3>
            <div className="flex justify-between items-center mb-3 text-xs font-bold">
              <span className="text-teal-500 flex items-center gap-1.5"><i className="fa-solid fa-thumbs-up"></i> ถูกใจ ({statsObj.totalLikes})</span>
              <span className="text-rose-500 flex items-center gap-1.5">ไม่ถูกใจ ({statsObj.totalDislikes}) <i className="fa-solid fa-thumbs-down"></i></span>
            </div>
            <div className="w-full h-4 bg-rose-500/20 dark:bg-rose-500/10 rounded-full overflow-hidden flex">
              <div
                className="h-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${statsObj.totalVotes > 0 ? (statsObj.totalLikes / statsObj.totalVotes) * 100 : 100}%` }}
              />
              <div
                className="h-full bg-rose-500 transition-all duration-500"
                style={{ width: `${statsObj.totalVotes > 0 ? (statsObj.totalDislikes / statsObj.totalVotes) * 100 : 0}%` }}
              />
            </div>
          </div>
          <div className="flex justify-between mt-4 text-[10px] text-slate-500 dark:text-slate-400 font-bold pt-3 border-t border-slate-100 dark:border-tuh-purple/10">
            <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalLikes / statsObj.totalVotes) * 100) : 100}% ประเมินเป็นบวก</span>
            <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalDislikes / statsObj.totalVotes) * 100) : 0}% ประเมินควรปรับปรุง</span>
          </div>
        </div>

        {/* Star rating distribution (Overall experience) */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-extrabold flex items-center gap-2">
              <i className="fa-solid fa-star text-amber-500"></i> ระดับคะแนนดาวประเมินบริการภาพรวม ({statsObj.totalStarsCount} การประเมิน)
            </h3>
            {statsObj.totalStarsCount > 0 && (
              <span className="text-sm font-black text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-xl border border-amber-500/20">
                {(
                  (statsObj.starCounts[5] * 5 +
                    statsObj.starCounts[4] * 4 +
                    statsObj.starCounts[3] * 3 +
                    statsObj.starCounts[2] * 2 +
                    statsObj.starCounts[1] * 1) /
                  statsObj.totalStarsCount
                ).toFixed(1)}{' '}
                / 5.0
              </span>
            )}
          </div>
          <div className="space-y-2.5">
            {[5, 4, 3, 2, 1].map((star) => {
              const count = statsObj.starCounts[star] || 0;
              const percentage = statsObj.totalStarsCount > 0 ? Math.round((count / statsObj.totalStarsCount) * 100) : 0;
              return (
                <div key={star} className="flex items-center gap-4 text-xs font-bold">
                  <span className="w-12 text-slate-500 dark:text-slate-400 flex items-center gap-1">
                    {star} ดาว <i className="fa-solid fa-star text-amber-400 text-[10px]"></i>
                  </span>
                  <div className="flex-1 h-3 bg-slate-100 dark:bg-tuh-indigo/20 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-400 transition-all duration-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-slate-700 dark:text-slate-200">
                    {count} คน ({percentage}%)
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Grid: 2 Comment Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Comments from Thumbs-Down clicks */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-100 dark:border-tuh-purple/10">
            <h3 className="text-base font-extrabold flex items-center gap-2">
              <i className="fa-solid fa-thumbs-down text-rose-500"></i> รายงานข้อเสนอแนะคำตอบที่ควรปรับปรุง ({statsObj.dislikeComments.length} ข้อความ)
            </h3>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {statsObj.dislikeComments.length === 0 ? (
              <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                ยังไม่มีข้อเสนอแนะจากคำตอบที่ควรปรับปรุงในช่วงเวลานี้
              </div>
            ) : (
              [...statsObj.dislikeComments].reverse().map(c => (
                <div key={c.id} className="p-4 tuh-glass-2 rounded-2xl flex gap-3 items-start shadow-sm hover:shadow-md transition duration-200">
                  <span className="w-9 h-9 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center shrink-0 text-base">
                    <i className="fa-solid fa-thumbs-down"></i>
                  </span>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex justify-between items-center pb-1.5 border-b border-slate-100 dark:border-tuh-purple/10">
                      <span className="text-xs text-slate-500 dark:text-slate-400 font-bold flex items-center gap-1">
                        <i className="fa-regular fa-clock"></i> {c.timestamp}
                      </span>
                    </div>

                    <div className="space-y-2 text-sm leading-relaxed">
                      {c.query && (
                        <div className="space-y-1">
                          <span className="text-xs font-black text-indigo-500 dark:text-indigo-400 flex items-center gap-1.5">
                            <i className="fa-solid fa-circle-question"></i> คำถามของผู้ใช้:
                          </span>
                          <p className="bg-white dark:bg-black/15 p-3 rounded-xl border border-slate-100 dark:border-tuh-purple/5 font-semibold text-slate-700 dark:text-slate-200 text-sm">
                            {c.query}
                          </p>
                        </div>
                      )}
                      {c.answer && (
                        <div className="space-y-1">
                          <span className="text-xs font-black text-rose-500 flex items-center gap-1.5">
                            <i className="fa-solid fa-robot"></i> คำตอบจากบอท:
                          </span>
                          <p className="bg-rose-500/5 dark:bg-rose-500/10 p-3 rounded-xl border border-rose-500/10 font-semibold text-slate-600 dark:text-slate-300 text-sm whitespace-pre-wrap">
                            {c.answer}
                          </p>
                        </div>
                      )}
                      <div className="space-y-1">
                        <span className="text-xs font-black text-teal-600 dark:text-teal-400 flex items-center gap-1.5">
                          <i className="fa-solid fa-comment-dots"></i> เหตุผลที่ควรปรับปรุง:
                        </span>
                        <p className="tuh-glass-2 p-3 rounded-xl font-bold text-slate-800 dark:text-white text-sm whitespace-pre-wrap">
                          {c.comment}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Comments from Star Ratings */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-100 dark:border-tuh-purple/10">
            <h3 className="text-base font-extrabold flex items-center gap-2">
              <i className="fa-solid fa-star text-amber-500"></i> ความคิดเห็นจากคะแนนดาวภาพรวม ({statsObj.starComments.length} ข้อความ)
            </h3>
          </div>

          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {statsObj.starComments.length === 0 ? (
              <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                ยังไม่มีความคิดเห็นจากคะแนนดาวในช่วงเวลานี้
              </div>
            ) : (
              [...statsObj.starComments].reverse().map(c => {
                const starsVal = c.stars !== undefined && c.stars !== null ? c.stars : (c.rating === 'like' ? 5 : 2);
                return (
                  <div key={c.id} className="p-4 tuh-glass-2 rounded-2xl flex gap-3 items-start shadow-sm hover:shadow-md transition duration-200">
                    <span className="w-16 px-1.5 py-1.5 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center gap-1 font-black text-xs shrink-0 border border-amber-500/20">
                      <i className="fa-solid fa-star"></i> {starsVal} ดาว
                    </span>
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex justify-between items-center pb-1.5 border-b border-slate-100 dark:border-tuh-purple/10">
                        <span className="text-xs text-slate-500 dark:text-slate-400 font-bold flex items-center gap-1">
                          <i className="fa-regular fa-clock"></i> {c.timestamp}
                        </span>
                      </div>
                      <div className="space-y-1">
                        <p className="bg-white dark:bg-black/15 p-3 rounded-xl border border-slate-100 dark:border-tuh-purple/5 font-bold text-slate-800 dark:text-white whitespace-pre-wrap text-sm">
                          {c.comment}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Custom Charts */}
      <div className="w-full">
        {/* Period chart data representation */}
        <div className="p-6 tuh-glass-1 rounded-3xl shadow-sm">
          <h3 className="text-base font-extrabold mb-5 flex items-center gap-2">
            <i className="fa-solid fa-chart-column text-tuh-rose"></i> การแจกแจงความพึงพอใจแยกตาม {satPeriod === 'daily' ? 'ช่วงเวลา' : satPeriod === 'weekly' ? 'วัน' : satPeriod === 'monthly' ? 'สัปดาห์' : 'เดือน'}
          </h3>

          <div className="space-y-4">
            {statsObj.chartData.length === 0 ? (
              <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                ไม่มีข้อมูลความพึงพอใจในช่วงเวลานี้
              </div>
            ) : (
              statsObj.chartData.map(item => (
                <div key={item.label} className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-slate-500 dark:text-slate-305">{item.label}</span>
                    <span className="text-slate-500 dark:text-slate-400 flex items-center gap-2">
                      <span className="text-teal-500">{item.likes} 👍</span>
                      <span className="text-rose-500">{item.dislikes} 👎</span>
                      <span className="bg-slate-100 dark:bg-black/25 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-extrabold">{item.rate}%</span>
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 dark:bg-tuh-navy/55 rounded-full overflow-hidden flex">
                    {/* แท่งแยกสีตามสัดส่วนจริง (ไลก์ = เขียว, ดิสไลก์ = แดง) แทนการโชว์แค่สัดส่วนไลก์
                        อย่างเดิม — ไม่งั้นวันที่มีแต่ดิสไลก์ล้วน (likes=0) จะกว้าง 0% เหมือนวันที่ไม่มีข้อมูลเลย
                        แยกไม่ออกว่า "ไม่มีข้อมูล" กับ "แย่ 100%" ต่างกันยังไง */}
                    <div
                      className="h-full bg-teal-500 transition-all duration-500"
                      style={{ width: `${item.total > 0 ? (item.likes / item.total) * 100 : 0}%` }}
                    />
                    <div
                      className="h-full bg-rose-500 transition-all duration-500"
                      style={{ width: `${item.total > 0 ? (item.dislikes / item.total) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
