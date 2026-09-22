import { useAdminContext } from '../context/AdminContext';
import StatCard from '../components/dashboard/StatCard';
import TrendLineChart from '../components/dashboard/TrendLineChart';
import CsatDoughnutChart from '../components/dashboard/CsatDoughnutChart';
import PendingQuestionsTable from '../components/dashboard/PendingQuestionsTable';
import ActiveAnnouncementsPanel from '../components/dashboard/ActiveAnnouncementsPanel';
import TrendDrawer from '../components/dashboard/TrendDrawer';
import AnswerFaqModal from '../components/dashboard/AnswerFaqModal';

/**
 * DashboardPage — แท็บ "ภาพรวม" หน้าแรกหลัง login (สรุปสถิติ, กราฟแนวโน้ม, comment ล่าสุด)
 * แยกออกมาจาก App.jsx เดิม (เคยเป็น IIFE ยาว ~580 บรรทัดฝังอยู่ใน return ของ App())
 *
 * ตัวหน้าเองยังคงเป็น consumer เดียวของ useAdminContext() (page component ไม่มี hook ของ
 * ตัวเองตามแผน) ส่วนกราฟ/ตาราง/การ์ด/modal ย่อยแยกเป็น component ใน components/dashboard/
 * รับข้อมูล/callback ผ่าน props ล้วนๆ เพื่อให้ใช้ซ้ำได้อิสระ ไม่ผูกกับ context โดยตรง
 */
export default function DashboardPage() {
  const {
    API_URL,
    analysisLoading,
    analysisResult,
    announcements,
    chunksMap,
    currentUnanswered,
    history,
    faqAnswer,
    handleSubmitFaq,
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
          <StatCard
            onClick={() => setActiveTab('logs')}
            gradientClasses="bg-gradient-to-br from-rose-500 to-pink-600"
            icon={<i className="fa-solid fa-circle-question"></i>}
            badge={
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 uppercase tracking-wider mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-300 animate-ping"></span>
                Action Required
              </span>
            }
            title="คำถามที่รอสอนบอท"
            value={
              <>
                <span className="text-3xl font-black">{pendingUnansweredCount}</span>
                <span className="text-xs font-bold opacity-80">คำถามค้างตอบ</span>
              </>
            }
            footerText="คลิกเพื่อเข้าไปตอบกลับ"
          />

          {/* Card 2: ความพึงพอใจเฉลี่ย */}
          <StatCard
            onClick={() => setActiveTab('satisfaction')}
            gradientClasses="bg-gradient-to-br from-emerald-500 to-teal-600"
            icon={<i className="fa-solid fa-face-smile"></i>}
            badge={
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                CSAT Score
              </span>
            }
            title="ความพึงพอใจเฉลี่ย"
            value={
              <>
                <span className="text-3xl font-black">
                  {stats.likes + stats.dislikes > 0 ? Math.round((stats.likes / (stats.likes + stats.dislikes)) * 100) : 100}%
                </span>
                <span className="text-xs font-bold opacity-80">จากประเมิน {stats.likes + stats.dislikes} ครั้ง</span>
              </>
            }
            footerText="ดูรายละเอียดสถิติ"
          />

          {/* Card 3: จำนวนการตอบของบอท */}
          <StatCard
            onClick={() => setActiveTab('history')}
            gradientClasses="bg-gradient-to-br from-sky-500 to-indigo-600"
            icon={<i className="fa-solid fa-clock-rotate-left"></i>}
            badge={
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                Bot Responses
              </span>
            }
            title="ยอดการตอบของบอท"
            value={
              <>
                <span className="text-3xl font-black">{stats.total_queries}</span>
                <span className="text-xs font-bold opacity-80">ถามตอบสะสม ({stats.queries_today} วันนี้)</span>
              </>
            }
            footerText="ประวัติความเร็วการตอบ"
          />

          {/* Card 4: จำนวนฐานข้อมูลคลังความรู้ */}
          <StatCard
            onClick={() => setActiveTab('documents')}
            gradientClasses="bg-gradient-to-br from-purple-500 to-fuchsia-600"
            icon={<i className="fa-solid fa-file-pdf"></i>}
            badge={
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-black bg-white/20 text-white backdrop-blur-sm border border-white/10 mb-2">
                Knowledge Bank
              </span>
            }
            title="ฐานข้อมูลเข้าระบบ RAG"
            value={
              <>
                <span className="text-3xl font-black">{stats.total_documents} PDF</span>
                <span className="text-xs font-bold opacity-80 font-black">/ {settings.predefined_faqs?.length || 0} FAQs</span>
              </>
            }
            footerText="จัดการคลังเอกสาร"
          />

        </div>

        {/* ส่วนที่ 2: กราฟแสดงสถิติและแนวโน้ม (Charts & Trends) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Line Chart: ประวัติการตอบและแนวโน้ม 7 วันย้อนหลัง */}
          <TrendLineChart
            history={history}
            unanswered={unanswered}
            parseTimestamp={parseTimestamp}
            isDarkMode={isDarkMode}
            onPointClick={setTrendDrawer}
          />

          {/* Doughnut Chart: อัตราความพึงพอใจการให้บริการ */}
          <CsatDoughnutChart stats={stats} />

        </div>

        {/* ส่วนที่ 3: รายการอัปเดตและงานที่ต้องทำ (Recent Activity & Tasks) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Table: ตารางรายการคำถามที่บอทตอบไม่ได้ */}
          <PendingQuestionsTable
            items={pendingUnanswered}
            onAnswerClick={(u) => {
              setCurrentUnanswered(u);
              setFaqAnswer('');
              setShowFaqModal(true);
            }}
          />

          {/* Right Column: รายการประกาศล่าสุดที่ Active */}
          <ActiveAnnouncementsPanel
            activeAnns={activeAnns}
            onManageClick={() => setActiveTab('announcements')}
          />

        </div>

      </div>

      {/* Slide-out panel: Q&A behind the clicked point on the trend chart */}
      <TrendDrawer
        trendDrawer={trendDrawer}
        onClose={() => setTrendDrawer(null)}
        chunksMap={chunksMap}
        API_URL={API_URL}
      />

      {/* MODAL: ANSWER FAQ MODAL — เปิดจากปุ่ม "เพิ่มใน FAQs" ของตารางคำถามที่บอทงงล่าสุดด้านบน */}
      <AnswerFaqModal
        show={showFaqModal}
        currentUnanswered={currentUnanswered}
        setCurrentUnanswered={setCurrentUnanswered}
        analysisLoading={analysisLoading}
        analysisResult={analysisResult}
        faqAnswer={faqAnswer}
        setFaqAnswer={setFaqAnswer}
        onClose={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
        onSubmit={handleSubmitFaq}
        showSuccess={showSuccess}
      />
    </>
  );
}
