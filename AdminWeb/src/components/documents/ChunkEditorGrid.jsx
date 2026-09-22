import ChunkCard from './ChunkCard';

/**
 * ChunkEditorGrid — แถบเครื่องมือเลือก/บันทึก chunk + ตารางการ์ดแก้ไข chunk ทั้งหมด
 * เดิมเป็น markup ที่ซ้ำกันเป๊ะๆ ใน DocumentsPage.jsx 2 จุด (modal พรีวิว pipeline ขั้นตอนที่ 3
 * และ modal แก้ไขรายละเอียดเอกสาร) ต่างกันแค่ขนาด/padding เล็กน้อยและ filename ที่ใช้ตอนบันทึก
 * จึงรวมเป็น component เดียว ควบคุมผ่าน prop `size` ('lg' สำหรับจุดแรก, 'sm' สำหรับจุดที่สอง)
 *
 * ตรรกะ onChange/toggle-select/auto-check-on-edit ทั้งหมดคงไว้ตรงตามเดิมทุกประการ
 */
export default function ChunkEditorGrid({
  chunks,
  setChunks,
  selectedIds,
  setSelectedIds,
  filename,
  savingContent,
  onSaveSelected,
  onSaveAll,
  onSaveIndividual,
  onExpand,
  size = 'lg',
}) {
  const isLg = size === 'lg';

  return (
    <>
      {/* Selective Saving Toolbar */}
      <div className={`flex flex-wrap items-center justify-between gap-3 tuh-glass-2 p-3 rounded-2xl ${isLg ? 'mb-3 ' : ''}text-xs font-bold`}>
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-300">
          <i className="fa-solid fa-list-check text-tuh-rose"></i>
          <span>เลือกแล้ว: <strong className="text-tuh-rose">{selectedIds.size}</strong> จาก <strong>{chunks.length}</strong> Chunks</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setSelectedIds(new Set(chunks.map(c => c.chunk_id)))}
            className={`${isLg ? 'px-3 py-1.5 rounded-xl' : 'px-2.5 py-1 rounded-lg'} bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 transition active:scale-95 text-slate-700 dark:text-slate-200`}
          >
            เลือกทั้งหมด
          </button>
          <button
            type="button"
            onClick={() => setSelectedIds(new Set())}
            className={`${isLg ? 'px-3 py-1.5 rounded-xl' : 'px-2.5 py-1 rounded-lg'} bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 transition active:scale-95 text-slate-700 dark:text-slate-200`}
          >
            ล้างการเลือก
          </button>
          <button
            type="button"
            disabled={selectedIds.size === 0 || savingContent}
            onClick={onSaveSelected}
            className={`${isLg ? 'px-3.5 py-1.5 rounded-xl' : 'px-3 py-1 rounded-lg'} bg-emerald-500 hover:bg-emerald-600 text-white hover:shadow transition active:scale-95 flex items-center gap-1 disabled:opacity-50 disabled:pointer-events-none`}
          >
            <i className="fa-solid fa-save"></i> บันทึกรายการที่เลือก
          </button>
          <button
            type="button"
            disabled={savingContent}
            onClick={onSaveAll}
            className={`${isLg ? 'px-3.5 py-1.5 rounded-xl' : 'px-3 py-1 rounded-lg'} bg-sky-500 hover:bg-sky-600 text-white hover:shadow transition active:scale-95 flex items-center gap-1 disabled:opacity-50`}
          >
            <i className="fa-solid fa-square-check"></i> บันทึกทั้งหมด
          </button>
        </div>
      </div>

      <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${isLg ? 'overflow-y-auto max-h-[50vh] pr-1' : 'max-h-[35vh] overflow-y-auto pr-1 custom-scrollbar'}`}>
        {chunks.map((c, i) => (
          <ChunkCard
            key={i}
            chunk={c}
            index={i}
            size={size}
            savingContent={savingContent}
            isSelected={selectedIds.has(c.chunk_id)}
            onToggleSelect={(checked) => {
              const newSet = new Set(selectedIds);
              if (checked) {
                newSet.add(c.chunk_id);
              } else {
                newSet.delete(c.chunk_id);
              }
              setSelectedIds(newSet);
            }}
            onContentChange={(newText) => {
              const updated = [...chunks];
              updated[i] = { ...c, content: newText };
              setChunks(updated);

              // Auto check on edit
              if (!selectedIds.has(c.chunk_id)) {
                const newSet = new Set(selectedIds);
                newSet.add(c.chunk_id);
                setSelectedIds(newSet);
              }
            }}
            onExpand={() => onExpand(c)}
            onSaveIndividual={() => onSaveIndividual(filename, c.chunk_id, c.content)}
          />
        ))}
      </div>
    </>
  );
}
