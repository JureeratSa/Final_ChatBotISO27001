/**
 * ChunkCard — การ์ดแก้ไขเนื้อหา 1 chunk (checkbox เลือก, ป้ายเลขหน้า, ปุ่มขยาย, textarea,
 * นับความยาวตัวอักษร, ปุ่มบันทึกเฉพาะ chunk นี้) ใช้ร่วมกันทั้ง 2 จุดที่เคยมี markup ซ้ำกัน
 * ใน DocumentsPage.jsx (modal พรีวิว pipeline และ modal แก้ไขรายละเอียดเอกสาร)
 *
 * `size` ควบคุมกลุ่ม className ที่เคยต่างกันเล็กน้อยระหว่าง 2 จุดเดิม (padding/ขนาดตัวอักษร/
 * ความสูง textarea) ให้ตรงกับของเดิมทุกประการ ไม่ปัดเป็นค่าเดียวกัน เพื่อไม่ให้หน้าตาเปลี่ยน
 */
export default function ChunkCard({
  chunk,
  index,
  isSelected,
  onToggleSelect,
  onContentChange,
  onExpand,
  onSaveIndividual,
  savingContent,
  size = 'lg',
}) {
  const isLg = size === 'lg';

  return (
    <div className={`p-4 ${isLg ? 'bg-slate-50' : 'bg-slate-50/50'} dark:bg-[#100220]/60 border rounded-2xl flex flex-col space-y-2 hover:border-tuh-rose/30 transition ${isSelected ? 'border-tuh-rose/50 dark:border-tuh-rose/40 shadow-sm' : 'border-slate-200/50 dark:border-tuh-purple/10'}`}>
      <div className={`flex justify-between items-center text-xs font-bold ${isLg ? 'text-slate-500' : 'text-slate-550'} dark:text-slate-400`}>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onToggleSelect(e.target.checked)}
            className="w-4 h-4 text-tuh-rose border-slate-300 rounded focus:ring-tuh-rose cursor-pointer"
          />
          <span className="text-tuh-navy dark:text-white">Chunk #{chunk.chunk_id || (index + 1)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="bg-tuh-rose/10 text-tuh-rose px-2 py-0.5 rounded-full text-[10px]">
            หน้า {chunk.metadata?.page || 1}
          </span>
          <button
            type="button"
            onClick={onExpand}
            className="p-1 text-slate-500 dark:text-slate-400 hover:text-tuh-rose hover:bg-slate-100/50 dark:hover:bg-white/10 rounded-lg transition"
            title="ขยายขนาดกล่องข้อความ"
          >
            <i className="fa-solid fa-expand text-xs"></i>
          </button>
        </div>
      </div>

      <div className="flex flex-col space-y-1.5 h-full">
        <textarea
          value={chunk.content}
          onChange={(e) => onContentChange(e.target.value)}
          className={`w-full ${isLg ? 'h-28 p-3' : 'h-24 p-2.5'} text-xs text-tuh-navy/90 dark:text-slate-200 leading-relaxed font-semibold tuh-glass-2 rounded-xl focus:outline-none focus:border-tuh-rose transition resize-none`}
          placeholder="เนื้อหาข้อมูลส่วนย่อย..."
        />
        <div className={`flex justify-between items-center ${isLg ? 'pt-1.5' : 'pt-1'} border-t border-slate-100 dark:border-white/5`}>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-bold">
            📏 {chunk.content?.length || 0} ตัวอักษร
          </span>
          <button
            disabled={savingContent}
            onClick={onSaveIndividual}
            className={`inline-flex items-center gap-1 ${isLg ? 'px-3 py-1' : 'px-2.5 py-1'} bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-lg ${isLg ? 'text-[10px]' : 'text-[9px]'} transition active:scale-95 disabled:opacity-50`}
            title="บันทึกเฉพาะ Chunk นี้"
          >
            {savingContent ? (
              <i className={`fa-solid fa-spinner animate-spin${isLg ? '' : ' text-[8px]'}`}></i>
            ) : (
              <i className={`fa-solid fa-save ${isLg ? 'text-[9px]' : 'text-[8px]'}`}></i>
            )}
            บันทึก Chunk
          </button>
        </div>
      </div>
    </div>
  );
}
