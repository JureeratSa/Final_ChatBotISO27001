import { useAdminContext } from '../context/AdminContext';
import ChunkEditorGrid from '../components/documents/ChunkEditorGrid';

/**
 * DocumentsPage — แท็บ "จัดการแฟ้มเอกสาร PDF" ครอบคลุมทั้ง pipeline อัปโหลด/คลีน/แบ่ง chunk
 * และแบบฟอร์มสวัสดิการ (Forms) รวมถึง modal ทั้งหมดของ flow นี้ (pre-upload, pipeline
 * preview, แก้ไขรายละเอียดเอกสาร, แก้ไข chunk แบบขยาย) — แยกออกมาจาก App.jsx เดิม
 */
export default function DocumentsPage() {
  const {
    API_URL,
    activeTab,
    approvingFilename,
    docCurrentPage,
    docSearchQuery,
    docSortField,
    docSortOrder,
    documents,
    dragOver,
    editDisplayName,
    expandedChunk,
    formName,
    formPage,
    formSearchQuery,
    forms,
    handleAddForm,
    handleApproveStep,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleOpenEditDocModal,
    handleSaveAllChunks,
    handleSaveContent,
    handleSaveDocDetails,
    handleSaveIndividualChunk,
    handleSaveSelectedChunks,
    handleSort,
    handleToggleDocStatus,
    handleViewPreview,
    loadingPreview,
    preDisplayName,
    preExcludePages,
    previewChunks,
    previewContent,
    previewFilename,
    previewModalType,
    savingContent,
    selectedChunkIds,
    selectedDoc,
    selectedFileForUpload,
    setDeleteModalState,
    setDocCurrentPage,
    setDocSearchQuery,
    setEditDisplayName,
    setExpandedChunk,
    setFormFile,
    setFormName,
    setFormPage,
    setFormSearchQuery,
    setPreDisplayName,
    setPreExcludePages,
    setPreviewChunks,
    setPreviewContent,
    setPreviewFilename,
    setPreviewModalType,
    setSelectedChunkIds,
    setSelectedDoc,
    setSelectedFileForUpload,
    setShowEditDocModal,
    setShowPreUploadModal,
    showEditDocModal,
    showPreUploadModal,
    stats,
    uploadFile,
    uploadProgress,
    uploading,
  } = useAdminContext();

  return (
    <>
            <div className="space-y-6 animate-slide-in">
              {/* Drag n Drop upload file container */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`p-10 border-2 border-dashed rounded-3xl text-center transition ${dragOver
                  ? 'border-tuh-rose bg-tuh-pink/20 dark:bg-tuh-rose/10'
                  : 'border-slate-300 dark:border-tuh-purple/30 bg-white dark:bg-[#2c0548]/25'
                  }`}
              >
                {uploading ? (
                  <div className="space-y-4 max-w-md mx-auto">
                    <div className="w-12 h-12 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin mx-auto"></div>
                    <h3 className="text-lg font-bold">กำลังอัปโหลดเอกสาร PDF... ({uploadProgress}%)</h3>
                    <div className="w-full bg-slate-100 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                      <div className="bg-tuh-rose h-full rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="text-5xl text-tuh-rose/60"><i className="fa-solid fa-cloud-arrow-up"></i></div>
                    <div>
                      <h3 className="text-lg font-extrabold text-tuh-navy dark:text-white">ลากและวางไฟล์ PDF ของคุณที่นี่</h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400 font-bold mt-1">ระบบรองรับไฟล์ระเบียบและเอกสารภาษาไทยนามสกุล PDF เท่านั้น</p>
                    </div>
                    <div>
                      <input
                        type="file"
                        id="pdf-uploader"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            const file = e.target.files[0];
                            setSelectedFileForUpload(file);
                            setPreExcludePages('');
                            setPreDisplayName(file.name);
                            setShowPreUploadModal(true);
                          }
                        }}
                      />
                      <label
                        htmlFor="pdf-uploader"
                        className="inline-flex items-center gap-2 bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2.5 px-6 rounded-2xl cursor-pointer active:scale-[0.98] transition"
                      >
                        <i className="fa-solid fa-file-circle-plus"></i> เลือกไฟล์จากคอมพิวเตอร์
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Documents Table */}
              {(() => {
                const filtered = documents.filter(doc =>
                  doc.filename.toLowerCase().includes(docSearchQuery.toLowerCase())
                );

                const sorted = [...filtered].sort((a, b) => {
                  let valA = a[docSortField];
                  let valB = b[docSortField];

                  if (docSortField === 'size' || docSortField === 'pages') {
                    valA = valA || 0;
                    valB = valB || 0;
                  } else if (docSortField === 'filename' || docSortField === 'upload_date' || docSortField === 'uploaded_by') {
                    valA = (valA || '').toLowerCase();
                    valB = (valB || '').toLowerCase();
                  }

                  if (valA < valB) return docSortOrder === 'asc' ? -1 : 1;
                  if (valA > valB) return docSortOrder === 'asc' ? 1 : -1;
                  return 0;
                });

                const totalDocs = sorted.length;
                const totalPages = Math.ceil(totalDocs / 5) || 1;
                const startIndex = (docCurrentPage - 1) * 5;
                const paginatedDocs = sorted.slice(startIndex, startIndex + 5);

                return (
                  <div className="tuh-glass-1 rounded-3xl overflow-hidden shadow-sm">
                    <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex items-center gap-4 flex-wrap">
                        <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-table text-tuh-rose"></i> แฟ้มเอกสารทั้งหมด</h3>
                        {stats.last_build_duration !== undefined && stats.last_build_duration !== null && (
                          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-black/20 px-3.5 py-1.5 rounded-full border border-slate-200/50 dark:border-tuh-purple/10">
                            ⏱️ สกัดเวกเตอร์ล่าสุดเสร็จสิ้นใน {stats.last_build_duration.toFixed(2)} วินาที
                          </span>
                        )}
                      </div>
                      {/* Search Bar */}
                      <div className="relative w-full md:w-72">
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-slate-500 dark:text-slate-400">
                          <i className="fa-solid fa-magnifying-glass text-xs"></i>
                        </span>
                        <input
                          type="text"
                          placeholder="ค้นหาเอกสารตามชื่อไฟล์..."
                          value={docSearchQuery}
                          onChange={(e) => setDocSearchQuery(e.target.value)}
                          className="w-full pl-9 pr-4 py-2.5 text-xs font-bold tuh-glass-2 rounded-2xl focus:outline-none focus:border-tuh-rose transition text-tuh-navy dark:text-white"
                        />
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20 select-none">
                            <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('filename')}>
                              ชื่อไฟล์
                              {docSortField === 'filename' ? (
                                docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                              ) : (
                                <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                              )}
                            </th>
                            <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('size')}>
                              ขนาดไฟล์
                              {docSortField === 'size' ? (
                                docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                              ) : (
                                <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                              )}
                            </th>
                            <th className="px-6 py-4 text-center cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('pages')}>
                              จำนวนหน้า
                              {docSortField === 'pages' ? (
                                docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                              ) : (
                                <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                              )}
                            </th>
                            <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('upload_date')}>
                              วันที่อัปโหลด
                              {docSortField === 'upload_date' ? (
                                docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                              ) : (
                                <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                              )}
                            </th>
                            <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('uploaded_by')}>
                              ผู้อัปโหลด
                              {docSortField === 'uploaded_by' ? (
                                docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                              ) : (
                                <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                              )}
                            </th>
                            <th className="px-6 py-4 text-center">สถานะการทำงาน</th>
                            <th className="px-6 py-4 text-center">เปิดใช้งาน</th>
                            <th className="px-6 py-4 text-right">เครื่องมือ</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                          {sorted.length === 0 ? (
                            <tr>
                              <td colSpan="8" className="px-6 py-8 text-center text-slate-500 dark:text-slate-400 font-bold">
                                {documents.length === 0 ? 'ไม่มีไฟล์เอกสารที่บันทึกไว้ในขณะนี้' : 'ไม่พบเอกสารที่ตรงกับการค้นหา'}
                              </td>
                            </tr>
                          ) : (
                            paginatedDocs.map(doc => {
                              const isProcessing = doc.status === 'Processing';
                              const isActive = doc.status === 'Active';
                              const isPipeline = ['Step_Raw_Text', 'Step_Clean_Text', 'Step_Chunk_Preview'].includes(doc.status);
                              return (
                                <tr key={doc.filename} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                                  <td className="px-6 py-4 font-bold max-w-[200px] truncate text-tuh-navy dark:text-white" title={doc.filename}>
                                    <a
                                      href={`${API_URL}/api/documents/download/${encodeURIComponent(doc.filename)}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="hover:text-tuh-rose hover:underline flex items-center transition"
                                    >
                                      <i className="fa-solid fa-file-pdf text-red-500 mr-2 shrink-0"></i>
                                      <span className="truncate">{doc.display_name || doc.filename}</span>
                                    </a>
                                  </td>
                                  <td className="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400">
                                    {Math.round(doc.size / 1024)} KB
                                  </td>
                                  <td className="px-6 py-4 text-center text-tuh-navy dark:text-slate-200">
                                    <div>{doc.pages || '-'} หน้า</div>
                                    {doc.exclude_pages && doc.exclude_pages.length > 0 && (
                                      <div className="text-[10px] text-red-500 font-bold bg-red-500/10 rounded-full px-2 py-0.5 inline-block mt-1">
                                        ละเว้นหน้า: {doc.exclude_pages.join(', ')}
                                      </div>
                                    )}
                                  </td>
                                  <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                                    {doc.upload_date}
                                  </td>
                                  <td className="px-6 py-4 text-xs font-bold text-slate-600 dark:text-slate-300">
                                    {doc.uploaded_by || 'ระบบ (Migration)'}
                                  </td>
                                  <td className="px-6 py-4 text-center">
                                    {isProcessing ? (
                                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-500">
                                        <i className="fa-solid fa-circle-notch animate-spin"></i>
                                        กำลังปรับปรุงฐานข้อมูล
                                      </span>
                                    ) : doc.status === 'Error' ? (
                                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-500">
                                        <i className="fa-solid fa-circle-xmark"></i>
                                        ผิดพลาด
                                      </span>
                                    ) : isPipeline ? (
                                      <div className="flex flex-col items-center">
                                        <div className="flex items-center gap-1 justify-center mt-1">
                                          <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Raw_Text' ? 'bg-amber-500 text-white animate-pulse' : 'bg-emerald-500 text-white'
                                            }`} title="สกัดข้อความดิบ">1</div>
                                          <div className={`w-4 h-0.5 ${doc.status !== 'Step_Raw_Text' ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                            }`} />
                                          <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Clean_Text' ? 'bg-amber-500 text-white animate-pulse' : (doc.status === 'Step_Chunk_Preview' || doc.status === 'Active') ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                            }`} title="คลีนข้อมูล">2</div>
                                          <div className={`w-4 h-0.5 ${(doc.status === 'Step_Chunk_Preview' || doc.status === 'Active') ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                            }`} />
                                          <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Chunk_Preview' ? 'bg-amber-500 text-white animate-pulse' : doc.status === 'Active' ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                            }`} title="แบ่งข้อมูล">3</div>
                                          <div className={`w-4 h-0.5 ${doc.status === 'Active' ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                            }`} />
                                          <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Active' ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                            }`} title="เวกเตอร์ทำงาน">4</div>
                                        </div>
                                        <div className="text-[10px] font-bold text-amber-500 mt-1">
                                          {doc.status === 'Step_Raw_Text' && '1. ตรวจคำดิบ'}
                                          {doc.status === 'Step_Clean_Text' && '2. ตรวจคำคลีน'}
                                          {doc.status === 'Step_Chunk_Preview' && '3. ตรวจส่วนย่อย (Chunk)'}
                                        </div>
                                      </div>
                                    ) : (
                                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500">
                                        <i className="fa-solid fa-circle-check"></i>
                                        พร้อมใช้งาน
                                      </span>
                                    )}
                                  </td>
                                  <td className="px-6 py-4 text-center">
                                    {isPipeline ? (
                                      <span className="text-xs font-bold text-amber-500 bg-amber-500/10 rounded-full px-2.5 py-1 inline-flex items-center gap-1">
                                        <i className="fa-solid fa-hourglass-half animate-spin"></i> รอนุมัติ
                                      </span>
                                    ) : (
                                      /* Status Toggle Switch */
                                      <button
                                        disabled={isProcessing}
                                        onClick={() => handleToggleDocStatus(doc.filename, doc.status)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${isActive ? 'bg-tuh-rose' : 'bg-slate-300 dark:bg-white/10'
                                          } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                      >
                                        <span
                                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isActive ? 'translate-x-6' : 'translate-x-1'
                                            }`}
                                        />
                                      </button>
                                    )}
                                  </td>
                                  <td className="px-6 py-4 text-right flex items-center justify-end gap-1.5">
                                    {isPipeline ? (
                                      <>
                                        {/* Preview Content Button */}
                                        <button
                                          onClick={() => {
                                            if (doc.status === 'Step_Raw_Text') handleViewPreview(doc.filename, 'raw');
                                            if (doc.status === 'Step_Clean_Text') handleViewPreview(doc.filename, 'cleaned');
                                            if (doc.status === 'Step_Chunk_Preview') handleViewPreview(doc.filename, 'chunks');
                                          }}
                                          className="inline-flex items-center gap-1 bg-sky-500 hover:bg-sky-600 text-white font-bold py-1.5 px-3 rounded-xl text-xs hover:shadow transition active:scale-95"
                                          title="ตรวจสอบเนื้อหาขั้นตอนนี้"
                                        >
                                          <i className="fa-solid fa-eye text-[11px]"></i> พรีวิว
                                        </button>
                                        {/* Approve Button */}
                                        <button
                                          disabled={approvingFilename === doc.filename}
                                          onClick={() => handleApproveStep(doc.filename, doc.status)}
                                          className="inline-flex items-center gap-1 bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-1.5 px-3 rounded-xl text-xs hover:shadow transition active:scale-95 disabled:opacity-50"
                                          title="อนุมัติเข้าสู่ขั้นตอนถัดไป"
                                        >
                                          {approvingFilename === doc.filename ? (
                                            <i className="fa-solid fa-spinner animate-spin"></i>
                                          ) : (
                                            <i className="fa-solid fa-circle-check text-[11px]"></i>
                                          )}
                                          อนุมัติ
                                        </button>
                                      </>
                                    ) : null}
                                    <button
                                      onClick={() => handleOpenEditDocModal(doc)}
                                      className="p-2 text-tuh-purple dark:text-tuh-purple-400 hover:bg-tuh-purple/10 rounded-xl transition active:scale-95 flex items-center justify-center disabled:opacity-50"
                                      title="แก้ไขรายละเอียดเอกสารและส่วนย่อย"
                                    >
                                      <i className="fa-solid fa-pen-to-square text-sm"></i>
                                    </button>
                                    <button
                                      disabled={approvingFilename === doc.filename}
                                      onClick={() => setDeleteModalState({ show: true, type: "document", targetId: doc.filename, targetName: doc.filename })}
                                      className="p-2 text-red-500 hover:bg-red-500/10 rounded-xl transition active:scale-95 flex items-center justify-center disabled:opacity-50"
                                      title="ลบเอกสาร"
                                    >
                                      <i className="fa-solid fa-trash-can text-sm"></i>
                                    </button>
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                      <div className="p-4 border-t border-slate-100 dark:border-tuh-purple/20 flex items-center justify-between flex-wrap gap-4 bg-slate-50/50 dark:bg-tuh-navy/10">
                        <div className="text-xs font-bold text-slate-500 dark:text-slate-400">
                          แสดง {startIndex + 1} ถึง {Math.min(startIndex + 5, totalDocs)} จากทั้งหมด {totalDocs} เอกสาร
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => setDocCurrentPage(prev => Math.max(prev - 1, 1))}
                            disabled={docCurrentPage === 1}
                            className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-tuh-purple/20 text-xs font-bold transition disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-white/5 active:scale-95 text-tuh-navy dark:text-white"
                          >
                            <i className="fa-solid fa-angle-left mr-1"></i> ก่อนหน้า
                          </button>

                          {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                            <button
                              key={pageNum}
                              onClick={() => setDocCurrentPage(pageNum)}
                              className={`w-8 h-8 rounded-lg text-xs font-extrabold transition active:scale-95 ${docCurrentPage === pageNum
                                ? 'bg-tuh-rose text-white shadow-sm'
                                : 'border border-slate-200 dark:border-tuh-purple/20 hover:bg-slate-50 dark:hover:bg-white/5 text-tuh-navy dark:text-white'
                                }`}
                            >
                              {pageNum}
                            </button>
                          ))}

                          <button
                            onClick={() => setDocCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            disabled={docCurrentPage === totalPages}
                            className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-tuh-purple/20 text-xs font-bold transition disabled:opacity-30 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-white/5 text-tuh-navy dark:text-white"
                          >
                            ถัดไป <i className="fa-solid fa-angle-right ml-1"></i>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Welfare Forms Management Panel */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
                {/* 1. Add Form Panel */}
                <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm">
                  <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2 mb-4">
                    <i className="fa-solid fa-file-circle-plus text-tuh-rose"></i> เพิ่มแบบฟอร์มสวัสดิการ
                  </h3>
                  <form onSubmit={handleAddForm} className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ชื่อแบบฟอร์ม <span className="text-red-500">*</span></label>
                      <input
                        type="text"
                        required
                        placeholder="เช่น แบบเสนอขอรับสวัสดิการ..."
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                        className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">อัปโหลดไฟล์แบบฟอร์ม (PDF) <span className="text-red-500">*</span></label>
                      <input
                        type="file"
                        id="form-file-uploader"
                        required
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setFormFile(e.target.files[0]);
                          }
                        }}
                        className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เลือกหน้าที่ต้องการตัดจาก PDF</label>
                      <input
                        type="text"
                        placeholder="เช่น 3 หรือ 1,3,5 หรือ 2-5 (ระบบจะตัดเฉพาะหน้าที่เลือกให้ User โหลด)"
                        value={formPage}
                        onChange={(e) => setFormPage(e.target.value)}
                        className="w-full tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2.5 px-6 rounded-2xl transition active:scale-[0.98] flex items-center justify-center gap-2 mt-2"
                    >
                      <i className="fa-solid fa-cloud-arrow-up"></i> บันทึกและอัปโหลดไฟล์
                    </button>
                  </form>
                </div>

                {/* 2. Forms List Panel */}
                <div className="lg:col-span-2 tuh-glass-1 rounded-3xl overflow-hidden shadow-sm flex flex-col">
                  <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                      <i className="fa-solid fa-folder-open text-tuh-rose"></i> แฟ้มแบบฟอร์มทั้งหมด ({forms.length} รายการ)
                    </h3>
                    {/* Search Bar for Forms */}
                    <div className="relative w-full md:w-60">
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-500 dark:text-slate-400">
                        <i className="fa-solid fa-magnifying-glass text-xs"></i>
                      </span>
                      <input
                        type="text"
                        placeholder="ค้นหาชื่อแบบฟอร์ม..."
                        value={formSearchQuery}
                        onChange={(e) => setFormSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 text-xs font-bold tuh-glass-2 rounded-2xl focus:outline-none focus:border-tuh-rose transition text-tuh-navy dark:text-white"
                      />
                    </div>
                  </div>

                  <div className="flex-1 overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                          <th className="px-6 py-3.5">ชื่อแบบฟอร์ม</th>
                          <th className="px-6 py-3.5">ไฟล์ PDF / หน้าที่ระบุ</th>
                          <th className="px-6 py-3.5 text-center">ดาวน์โหลด</th>
                          <th className="px-6 py-3.5 text-right">จัดการ</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                        {(() => {
                          const filtered = forms.filter(form =>
                            form.name.toLowerCase().includes(formSearchQuery.toLowerCase())
                          );

                          if (filtered.length === 0) {
                            return (
                              <tr>
                                <td colSpan="4" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-bold">
                                  {forms.length === 0 ? 'ยังไม่มีแบบฟอร์มที่ลงทะเบียนไว้ในแฟ้มข้อมูล' : 'ไม่พบแบบฟอร์มที่ตรงกับการค้นหา'}
                                </td>
                              </tr>
                            );
                          }

                          return filtered.map((form) => (
                            <tr key={form.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              <td className="px-6 py-4 font-bold text-tuh-navy dark:text-white">
                                <i className="fa-regular fa-file-lines text-teal-500 mr-2"></i>
                                {form.name}
                              </td>
                              <td className="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400">
                                <div className="flex flex-col gap-0.5">
                                  <span className="truncate max-w-[180px] block text-tuh-navy dark:text-slate-200" title={form.filename ? form.filename.substring(form.filename.indexOf('_') + 1) : ''}>
                                    <i className="fa-solid fa-file-pdf text-red-500 mr-1.5"></i>
                                    {form.filename ? form.filename.substring(form.filename.indexOf('_') + 1) : 'ไม่มีไฟล์'}
                                  </span>
                                  {form.page && <span className="text-sm font-extrabold text-tuh-rose">หน้า {form.page}</span>}
                                </div>
                              </td>
                              <td className="px-6 py-4 text-center">
                                <a
                                  href={form.page ? `${form.link}#page=${form.page}` : form.link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 transition"
                                  title="เปิดดู / ดาวน์โหลดเอกสาร PDF"
                                >
                                  <i className="fa-solid fa-arrow-down-long text-xs"></i>
                                </a>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <button
                                  onClick={() => setDeleteModalState({ show: true, type: 'form', targetId: form.id, targetName: form.name })}
                                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-xl transition active:scale-95 inline-flex items-center justify-center"
                                  title="ลบแบบฟอร์ม"
                                >
                                  <i className="fa-solid fa-trash-can text-sm"></i>
                                </button>
                              </td>
                            </tr>
                          ));
                        })()}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

            </div>

      {/* MODAL: PRE-UPLOAD CONFIGURE EXCLUDE PAGES MODAL */}
      {showPreUploadModal && selectedFileForUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-file-circle-plus text-tuh-rose"></i> ตั้งค่าการนำเข้าและละเว้นหน้า
              </h3>
              <button
                onClick={() => { setShowPreUploadModal(false); setSelectedFileForUpload(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setShowPreUploadModal(false);
                uploadFile(selectedFileForUpload, preExcludePages, preDisplayName);
                setSelectedFileForUpload(null);
              }}
              className="p-6 space-y-4"
            >
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ไฟล์ที่เลือก</label>
                <div className="p-4 tuh-glass-2 rounded-2xl font-bold text-sm truncate text-tuh-navy dark:text-white">
                  {selectedFileForUpload.name}
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  ชื่อที่จะให้แสดงในคอลัมน์ชื่อไฟล์ ตารางแฟ้มเอกสารทั้งหมด
                </label>
                <input
                  type="text"
                  placeholder="กรอกชื่อที่จะให้แสดงในตาราง..."
                  value={preDisplayName}
                  onChange={(e) => setPreDisplayName(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-tuh-navy dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  ระบุหมายเลขหน้าที่ต้องการ "ละเว้น" (ถ้ามี)
                </label>
                <input
                  type="text"
                  placeholder="ระบุเลขหน้า เช่น 12, 13, 14, 18 (คั่นด้วยจุลภาค ,) หรือปล่อยว่างไว้"
                  value={preExcludePages}
                  onChange={(e) => setPreExcludePages(e.target.value)}
                  className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-tuh-navy dark:text-white"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1.5 leading-relaxed">
                  💡 หน้านโยบายเปล่า, หน้าภาคผนวก, หน้าคำลงท้าย, หรือหน้าปกที่บอทไม่ต้องนำมาสืบค้น สามารถกรอกเพื่อข้ามหน้าเหล่านั้นได้ตั้งแต่แรก
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowPreUploadModal(false); setSelectedFileForUpload(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-cloud-arrow-up mr-1.5"></i> เริ่มอัปโหลดและประมวลผล
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: PIPELINE WORKFLOW CONTENT PREVIEW MODAL */}
      {previewModalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-4xl tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-square-poll-horizontal text-tuh-rose"></i>
                ตรวจสอบและแก้ไขข้อมูล: {previewFilename}
                <span className="text-xs bg-amber-500/10 text-amber-500 py-1 px-3 rounded-full font-bold ml-2">
                  {previewModalType === 'raw' && 'ขั้นตอนที่ 1: คำดิบจาก PDF (สามารถแก้ไขได้)'}
                  {previewModalType === 'cleaned' && 'ขั้นตอนที่ 2: ข้อความหลังคลีน (Markdown) (สามารถแก้ไขได้)'}
                  {previewModalType === 'chunks' && 'ขั้นตอนที่ 3: ส่วนย่อยสำหรับสืบค้น (Chunks) (สามารถแก้ไขได้)'}
                </span>
              </h3>
              <button
                onClick={() => { setPreviewModalType(null); setPreviewFilename(''); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div className="p-6">
              {loadingPreview ? (
                <div className="py-20 flex flex-col items-center justify-center space-y-4">
                  <div className="w-12 h-12 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin"></div>
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-bold">กำลังดึงข้อมูลพรีวิว...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {previewModalType === 'chunks' ? (
                    <ChunkEditorGrid
                      size="lg"
                      chunks={previewChunks}
                      setChunks={setPreviewChunks}
                      selectedIds={selectedChunkIds}
                      setSelectedIds={setSelectedChunkIds}
                      filename={previewFilename}
                      savingContent={savingContent}
                      onSaveSelected={() => handleSaveSelectedChunks(previewFilename)}
                      onSaveAll={() => handleSaveAllChunks(previewFilename)}
                      onSaveIndividual={handleSaveIndividualChunk}
                      onExpand={setExpandedChunk}
                    />
                  ) : (
                    <div>
                      <div className="text-xs font-bold text-slate-500 dark:text-slate-400 mb-2">
                        {previewModalType === 'raw' ? '📝 แก้ไขข้อมูลตัวอักษรดิบที่สกัดจากหน้าเอกสาร:' : '📝 แก้ไขข้อมูลมาร์กดาวน์หลังแปลงรูปแบบและแปลงเลขไทย:'}
                      </div>
                      <textarea
                        value={previewContent}
                        onChange={(e) => setPreviewContent(e.target.value)}
                        className="w-full h-[55vh] p-5 font-mono text-xs leading-relaxed border border-slate-200/50 dark:border-slate-700 rounded-2xl bg-slate-50 text-slate-800 dark:bg-[#100220] dark:text-slate-200 focus:outline-none focus:border-tuh-rose transition resize-none custom-scrollbar"
                        placeholder="กรอก/แก้ไขเนื้อหาเอกสารที่นี่..."
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-6 border-t border-slate-100 dark:border-tuh-purple/20 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setPreviewModalType(null); setPreviewFilename(''); }}
                className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
              >
                ปิดหน้าต่าง
              </button>
              {previewModalType !== 'chunks' && (
                <button
                  type="button"
                  disabled={savingContent}
                  onClick={() => handleSaveContent(previewFilename, previewModalType, previewContent)}
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
                >
                  {savingContent ? (
                    <i className="fa-solid fa-spinner animate-spin"></i>
                  ) : (
                    <i className="fa-solid fa-save"></i>
                  )}
                  บันทึกการแก้ไข
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT DOCUMENT DETAILS AND CHUNKS */}
      {showEditDocModal && selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-4xl tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-file-pen text-tuh-rose"></i>
                แก้ไขรายละเอียดเอกสาร: {selectedDoc.filename}
              </h3>
              <button
                onClick={() => { setShowEditDocModal(false); setSelectedDoc(null); setPreviewChunks([]); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto custom-scrollbar">
              {/* Part 1: Edit Document Metadata */}
              <form onSubmit={handleSaveDocDetails} className="space-y-4 tuh-glass-2 p-5 rounded-2xl">
                <h4 className="font-bold text-sm text-tuh-rose flex items-center gap-1.5">
                  <i className="fa-solid fa-circle-info"></i> ข้อมูลทั่วไปของไฟล์
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ชื่อจริงของไฟล์ (แก้ไขไม่ได้)</label>
                    <div className="p-3 bg-slate-100 dark:bg-[#100220]/60 rounded-xl font-bold border border-slate-200/50 dark:border-tuh-purple/10 text-xs truncate text-slate-500 dark:text-slate-400">
                      {selectedDoc.filename}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-550 dark:text-slate-400 mb-1.5">ชื่อที่จะให้แสดงในคอลัมน์ชื่อไฟล์</label>
                    <input
                      type="text"
                      required
                      value={editDisplayName}
                      onChange={(e) => setEditDisplayName(e.target.value)}
                      placeholder="ระบุชื่อที่ต้องการให้แสดง..."
                      className="w-full tuh-glass-1 rounded-xl py-2 px-3 focus:outline-none focus:border-tuh-rose transition font-semibold text-xs text-tuh-navy dark:text-white"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="bg-tuh-gradient-2 text-white font-bold py-2 px-5 rounded-xl text-xs hover:shadow transition active:scale-[0.98] flex items-center gap-1.5"
                  >
                    <i className="fa-solid fa-floppy-disk"></i> บันทึกการแก้ไขข้อมูลทั่วไป
                  </button>
                </div>
              </form>

              {/* Part 2: Edit Chunks */}
              <div className="space-y-3">
                <h4 className="font-bold text-sm text-tuh-rose flex items-center gap-1.5">
                  <i className="fa-solid fa-square-poll-horizontal"></i> ส่วนย่อยสำหรับสืบค้น (Chunks) สำหรับนำเข้า RAG
                </h4>

                {loadingPreview ? (
                  <div className="py-12 flex flex-col items-center justify-center space-y-3">
                    <div className="w-10 h-10 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin"></div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-bold">กำลังโหลดส่วนย่อย (Chunks)...</p>
                  </div>
                ) : previewChunks.length > 0 ? (
                  <div className="space-y-4">
                    <ChunkEditorGrid
                      size="sm"
                      chunks={previewChunks}
                      setChunks={setPreviewChunks}
                      selectedIds={selectedChunkIds}
                      setSelectedIds={setSelectedChunkIds}
                      filename={selectedDoc.filename}
                      savingContent={savingContent}
                      onSaveSelected={() => handleSaveSelectedChunks(selectedDoc.filename)}
                      onSaveAll={() => handleSaveAllChunks(selectedDoc.filename)}
                      onSaveIndividual={handleSaveIndividualChunk}
                      onExpand={setExpandedChunk}
                    />
                  </div>
                ) : (
                  <div className="p-6 bg-slate-100/50 dark:bg-[#100220]/20 rounded-2xl text-center border border-dashed border-slate-200 dark:border-tuh-purple/20 text-xs font-bold text-slate-550 dark:text-slate-400">
                    💡 เอกสารนี้ยังไม่ได้ผ่านการแบ่งข้อมูล (Chunking) จึงยังไม่มี Chunks ให้แก้ไข (สถานะปัจจุบัน: {selectedDoc.status})
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-slate-100 dark:border-tuh-purple/20 flex justify-end gap-3 bg-slate-50 dark:bg-tuh-navy/55">
              <button
                type="button"
                onClick={() => { setShowEditDocModal(false); setSelectedDoc(null); setPreviewChunks([]); }}
                className="px-5 py-2.5 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-white/5 dark:hover:bg-white/10 dark:text-slate-350 font-bold transition active:scale-95 text-xs"
              >
                ปิดหน้าต่าง
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SUB-MODAL FOR EXPANDED/ZOOMED CHUNK EDITING */}
      {expandedChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
          <div className="w-full max-w-3xl tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h4 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-expand text-tuh-rose"></i>
                แก้ไขคำอธิบายส่วนย่อย: Chunk #{expandedChunk.chunk_id} (หน้า {expandedChunk.metadata?.page || 1})
              </h4>
              <button
                onClick={() => setExpandedChunk(null)}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <textarea
                value={expandedChunk.content}
                onChange={(e) => {
                  const newText = e.target.value;
                  setExpandedChunk({ ...expandedChunk, content: newText });

                  const idx = previewChunks.findIndex(x => x.chunk_id === expandedChunk.chunk_id);
                  if (idx !== -1) {
                    const updated = [...previewChunks];
                    updated[idx] = { ...updated[idx], content: newText };
                    setPreviewChunks(updated);

                    if (!selectedChunkIds.has(expandedChunk.chunk_id)) {
                      const newSet = new Set(selectedChunkIds);
                      newSet.add(expandedChunk.chunk_id);
                      setSelectedChunkIds(newSet);
                    }
                  }
                }}
                className="w-full h-[50vh] p-5 font-semibold text-sm leading-relaxed border border-slate-200/50 dark:border-slate-700 rounded-2xl bg-slate-50 text-slate-800 dark:bg-[#100220] dark:text-slate-200 focus:outline-none focus:border-tuh-rose transition resize-none custom-scrollbar"
                placeholder="พิมพ์แก้ไขเนื้อหาของ Chunk นี้ในขนาดที่ใหญ่ขึ้น..."
              />
              <div className="text-xs text-slate-500 dark:text-slate-400 font-bold">
                📏 ความยาวปัจจุบัน: {expandedChunk.content?.length || 0} ตัวอักษร
              </div>
            </div>

            <div className="p-6 border-t border-slate-100 dark:border-tuh-purple/20 flex justify-end gap-3 bg-slate-50/50 dark:bg-tuh-navy/20">
              <button
                type="button"
                onClick={() => setExpandedChunk(null)}
                className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
              >
                ย้อนกลับ
              </button>
              <button
                type="button"
                disabled={savingContent}
                onClick={() => {
                  handleSaveIndividualChunk(previewFilename, expandedChunk.chunk_id, expandedChunk.content);
                  setExpandedChunk(null);
                }}
                className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center gap-1.5"
              >
                {savingContent ? (
                  <i className="fa-solid fa-spinner animate-spin"></i>
                ) : (
                  <i className="fa-solid fa-check"></i>
                )}
                ยืนยันและบันทึกด่วน
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
