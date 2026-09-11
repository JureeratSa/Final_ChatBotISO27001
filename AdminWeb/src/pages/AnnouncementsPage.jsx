import { useAdminContext } from '../context/AdminContext';
import CKEditorWrapper from '../components/CKEditorWrapper';

/**
 * AnnouncementsPage — แท็บ "สร้างและจัดการประกาศ" ทั้งฟอร์มสร้าง/แก้ไข (rich text + กำหนดเวลา)
 * และรายการประกาศทั้งหมดพร้อมตัวกรองสถานะ — แยกออกมาจาก App.jsx เดิม
 */
export default function AnnouncementsPage() {
  const {
    annCategory,
    annContent,
    annEndDate,
    annFilter,
    annPinned,
    annStartDate,
    annTitle,
    announcements,
    departments,
    editingAnnId,
    handleCancelEditAnnouncement,
    handleCreateAnnouncement,
    handleEditAnnouncement,
    isAnnFormOpen,
    isDarkMode,
    setAnnCategory,
    setAnnContent,
    setAnnEndDate,
    setAnnFilter,
    setAnnPinned,
    setAnnStartDate,
    setAnnTitle,
    setDeleteModalState,
    setEditingAnnId,
    setIsAnnFormOpen,
  } = useAdminContext();

  return (
    <div className="w-full">
      {isAnnFormOpen ? (
        /* Form to create/edit announcement (Matching Image 2 layout) */
        <form onSubmit={handleCreateAnnouncement} className="space-y-6 animate-slide-in">
          {/* Form Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 tuh-glass-1 rounded-3xl p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleCancelEditAnnouncement}
                className="flex items-center justify-center w-10 h-10 rounded-full tuh-glass-3 hover:bg-slate-50 dark:hover:bg-tuh-purple/10 text-slate-700 dark:text-slate-250 transition active:scale-95"
                title="ย้อนกลับ"
              >
                <i className="fa-solid fa-arrow-left text-sm"></i>
              </button>
              <div>
                <h3 className="text-lg font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                  <i className="fa-solid fa-bullhorn text-tuh-rose"></i> {editingAnnId ? "แก้ไขประกาศ" : "สร้างประกาศใหม่"}
                </h3>
                <p className="text-xs font-semibold text-slate-450 dark:text-slate-350">
                  {editingAnnId ? "แก้ไขรายละเอียดและกำหนดเวลาแสดงประกาศ" : "กรอกข้อมูลและกำหนดเวลาแสดงประกาศข่าวใหม่"}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCancelEditAnnouncement}
                className="px-5 py-2.5 rounded-2xl tuh-glass-3 hover:bg-slate-50 dark:hover:bg-tuh-purple/10 text-slate-700 dark:text-slate-200 text-sm font-bold transition active:scale-95"
              >
                กลับ
              </button>
              <button
                type="submit"
                className="bg-tuh-gradient-2 text-white text-sm font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center gap-2"
              >
                <i className="fa-solid fa-check-circle"></i> บันทึก
              </button>
            </div>
          </div>

          {/* Form Layout Split: Left (Content) / Right (Settings) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* LEFT: Content Fields (2 Columns) */}
            <div className="lg:col-span-2 space-y-6">
              <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm space-y-4">
                <h4 className="text-sm font-extrabold text-tuh-navy dark:text-white uppercase tracking-wider border-b border-slate-100 dark:border-tuh-purple/10 pb-2">
                  เนื้อหาข่าว / ประกาศ
                </h4>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    เรื่อง / หัวข้อประกาศ *
                  </label>
                  <input
                    type="text"
                    placeholder="กรอกหัวข้อประกาศ..."
                    value={annTitle}
                    onChange={(e) => setAnnTitle(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    เนื้อหาประกาศ (Rich text) *
                  </label>
                  <CKEditorWrapper
                    value={annContent}
                    onChange={(data) => setAnnContent(data)}
                    isDarkMode={isDarkMode}
                  />
                </div>
              </div>
            </div>

            {/* RIGHT: Settings/Sidebar (1 Column) */}
            <div className="lg:col-span-1 space-y-6">
              <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm space-y-5">
                <h4 className="text-sm font-extrabold text-tuh-navy dark:text-white uppercase tracking-wider border-b border-slate-100 dark:border-tuh-purple/10 pb-2 flex items-center gap-2">
                  <i className="fa-solid fa-sliders"></i> การตั้งค่า
                </h4>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    สถานะประกาศ
                  </label>
                  <div className="mt-1">
                    {!annStartDate || !annEndDate ? (
                      <span className="inline-flex items-center px-3 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 rounded-full text-xs font-bold border border-slate-200 dark:border-slate-700">
                        ฉบับร่าง (ยังกำหนดเวลาไม่ครบ)
                      </span>
                    ) : (() => {
                      const now = new Date();
                      const start = new Date(annStartDate);
                      const end = new Date(annEndDate);
                      if (now < start) return <span className="inline-flex items-center px-3 py-1.5 bg-amber-500/10 text-amber-500 border border-amber-500/25 rounded-full text-xs font-bold">รอการแสดงผล</span>;
                      if (now > end) return <span className="inline-flex items-center px-3 py-1.5 bg-slate-500/10 text-slate-450 border border-slate-500/25 rounded-full text-xs font-bold">หมดระยะเวลา</span>;
                      return <span className="inline-flex items-center px-3 py-1.5 bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 rounded-full text-xs font-bold animate-pulse">กำลังแสดงผล</span>;
                    })()}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    วันและเวลาเริ่มแสดงประกาศ *
                  </label>
                  <input
                    type="datetime-local"
                    value={annStartDate}
                    onChange={(e) => setAnnStartDate(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    วันและเวลาสิ้นสุดประกาศ *
                  </label>
                  <input
                    type="datetime-local"
                    value={annEndDate}
                    onChange={(e) => setAnnEndDate(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    หมวดประกาศ (Department Link)
                  </label>
                  <select
                    value={annCategory}
                    onChange={(e) => setAnnCategory(e.target.value)}
                    className="w-full tuh-glass-2 rounded-2xl py-2.5 px-3 focus:outline-none focus:border-tuh-rose transition font-bold text-xs text-tuh-navy dark:text-white h-11"
                  >
                    <option value="">-- ไม่ระบุหมวด --</option>
                    {departments.map((dept) => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                    {departments.length === 0 && (
                      <option value="ทั่วไป">ทั่วไป</option>
                    )}
                  </select>
                </div>

                {/* Pin Toggle Switch (Interactive) */}
                <div className="border-t border-slate-100 dark:border-tuh-purple/10 pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="block text-xs font-bold text-tuh-navy dark:text-white">ปักหมุดข่าวประกาศ</span>
                      <span className="block text-[10px] font-semibold text-slate-400">แสดงข่าวไว้ที่ด้านบนสุดเสมอ</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={annPinned}
                        onChange={(e) => setAnnPinned(e.target.checked)}
                      />
                      <div className="w-9 h-5 bg-slate-200 dark:bg-tuh-navy/55 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </form>
      ) : (
        /* Full width announcements list */
        <div className="w-full space-y-4 animate-slide-in">
          <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 dark:border-tuh-purple/10 pb-4 mb-4">
              <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-list-check text-tuh-rose"></i> รายการประกาศทั้งหมด ({announcements.length})
              </h3>
              <div className="flex items-center gap-3">
                {/* Dropdown for Status Filter */}
                <select
                  value={annFilter}
                  onChange={(e) => setAnnFilter(e.target.value)}
                  className="tuh-glass-2 rounded-2xl py-2 px-4 focus:outline-none focus:border-tuh-rose text-xs font-bold text-tuh-navy dark:text-white transition h-10 cursor-pointer"
                >
                  <option value="all">ทั้งหมด ({announcements.length})</option>
                  <option value="active">
                    ดำเนินการ ({announcements.filter(ann => {
                      const now = new Date();
                      return now >= new Date(ann.start_date) && now <= new Date(ann.end_date);
                    }).length})
                  </option>
                  <option value="expired">
                    หมดระยะเวลา ({announcements.filter(ann => {
                      const now = new Date();
                      return now > new Date(ann.end_date);
                    }).length})
                  </option>
                  <option value="pending">
                    รอแสดงผล ({announcements.filter(ann => {
                      const now = new Date();
                      return now < new Date(ann.start_date);
                    }).length})
                  </option>
                </select>

                <button
                  type="button"
                  onClick={() => {
                    setIsAnnFormOpen(true);
                    setEditingAnnId(null);
                    setAnnTitle('');
                    setAnnContent('');
                    setAnnStartDate('');
                    setAnnEndDate('');
                    setAnnPinned(false);
                  }}
                  className="bg-tuh-rose hover:bg-tuh-rose/90 text-white font-extrabold py-2 px-5 rounded-2xl transition active:scale-[0.98] flex items-center gap-2 text-xs h-10"
                >
                  <i className="fa-solid fa-plus-circle"></i> เพิ่มประกาศใหม่
                </button>
              </div>
            </div>

            {announcements.length === 0 ? (
              <div className="text-center py-12 text-slate-400 dark:text-slate-300 font-bold">
                <i className="fa-solid fa-bullhorn text-4xl mb-3 block opacity-30"></i>
                ไม่มีประกาศในระบบขณะนี้
              </div>
            ) : (() => {
              const filteredAnnouncements = announcements.filter((ann) => {
                const now = new Date();
                const start = new Date(ann.start_date);
                const end = new Date(ann.end_date);
                if (annFilter === 'active') {
                  return now >= start && now <= end;
                } else if (annFilter === 'expired') {
                  return now > end;
                } else if (annFilter === 'pending') {
                  return now < start;
                }
                return true;
              });

              if (filteredAnnouncements.length === 0) {
                return (
                  <div className="text-center py-12 text-slate-400 dark:text-slate-300 font-bold">
                    <i className="fa-solid fa-filter-circle-xmark text-4xl mb-3 block opacity-30"></i>
                    ไม่มีประกาศตามเงื่อนไขตัวกรองที่เลือก
                  </div>
                );
              }

              // Sort: Pinned first
              const sortedAnnouncements = [...filteredAnnouncements].sort((a, b) => {
                const aPinned = a.pinned ? 1 : 0;
                const bPinned = b.pinned ? 1 : 0;
                return bPinned - aPinned;
              });

              return (
                <div className="grid grid-cols-1 gap-4">
                  {sortedAnnouncements.map((ann) => {
                    const now = new Date();
                    const start = new Date(ann.start_date);
                    const end = new Date(ann.end_date);
                    let statusBadge = null;

                    if (now < start) {
                      statusBadge = <span className="bg-amber-500/10 text-amber-500 border border-amber-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold">รอแสดงผล</span>;
                    } else if (now > end) {
                      statusBadge = <span className="bg-slate-500/10 text-slate-450 border border-slate-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold">หมดระยะเวลา</span>;
                    } else {
                      statusBadge = <span className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold animate-pulse">กำลังแสดงผล</span>;
                    }

                    return (
                      <div key={ann.id} className="p-5 rounded-2xl tuh-glass-2 flex flex-col justify-between gap-4 hover:shadow-md transition">
                        <div className="flex justify-between items-start gap-4">
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              {ann.pinned && (
                                <span className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold flex items-center gap-1">
                                  <i className="fa-solid fa-thumbtack text-[10px]"></i> ปักหมุด
                                </span>
                              )}
                              <h4 className="font-extrabold text-tuh-navy dark:text-white text-base">{ann.title}</h4>
                              {ann.category && (
                                <span className="bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold">
                                  {ann.category}
                                </span>
                              )}
                              {statusBadge}
                            </div>
                            <div
                              className="text-sm font-semibold text-slate-650 dark:text-slate-350 leading-relaxed html-content font-sans"
                              dangerouslySetInnerHTML={{ __html: ann.content }}
                            />
                          </div>
                          <div className="flex gap-1 shrink-0">
                            <button
                              onClick={() => handleEditAnnouncement(ann)}
                              className="p-2 rounded-xl text-tuh-purple dark:text-tuh-purple-400 hover:bg-tuh-purple/10 transition active:scale-95"
                              title="แก้ไขประกาศ"
                            >
                              <i className="fa-solid fa-pen-to-square text-lg"></i>
                            </button>
                            <button
                              onClick={() => setDeleteModalState({ show: true, type: 'announcement', targetId: ann.id, targetName: ann.title })}
                              className="p-2 rounded-xl text-red-500 hover:bg-red-500/10 hover:text-red-650 transition active:scale-95"
                              title="ลบประกาศ"
                            >
                              <i className="fa-solid fa-trash-can text-lg"></i>
                            </button>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-300 border-t border-slate-100 dark:border-tuh-purple/5 pt-3 font-semibold gap-2">
                          <div>
                            <i className="fa-regular fa-clock mr-1"></i>
                            เริ่ม: {ann.start_date.replace("T", " ")} | สิ้นสุด: {ann.end_date.replace("T", " ")}
                          </div>
                          <div>
                            {ann.created_by && <span className="mr-3 font-bold text-slate-650 dark:text-slate-300"><i className="fa-solid fa-user mr-1"></i> ผู้เขียน: {ann.created_by}</span>}
                            สร้างเมื่อ: {ann.created_at}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
