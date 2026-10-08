import { useEffect, useState } from 'react';
import { useAdminContext } from '../../context/AdminContext';

/**
 * TeachFromDocumentPanel — "สอนบอทผ่านเอกสาร" ใน ResolveUnansweredModal (กรณีเอกสารมีคำตอบแล้ว)
 *
 *   diagnose → ทดสอบค้นหาด้วยคำถามเดิม (ไม่เรียก LLM ไม่บันทึกประวัติ) แสดง 10 อันดับแรก
 *              แอดมินเลือก chunk ที่มีคำตอบ หรือค้นหาข้อความในเอกสารถ้าไม่ติดอันดับ
 *   hint     → AI เสนอคำถามตัวอย่าง แอดมินแก้/เพิ่ม/ลบ แล้วบันทึก (นำเข้าดัชนีทันที)
 *   verified → ระบบค้นซ้ำด้วยคำถามเดิมเพื่อยืนยันว่า chunk ขึ้นมาอยู่ในอันดับที่ส่งให้บอทแล้ว
 *
 * คำถามตัวอย่างใช้เฉพาะตอนค้นหา — คำตอบยังมาจากเนื้อหา PDF เดิมพร้อมลิงก์อ้างอิง ไม่ต้องเพิ่ม FAQ
 */
export default function TeachFromDocumentPanel({ item, onBack, onUseFaq, onDone, setBusy }) {
  const {
    handleResolveUnanswered,
    ragSearchChunks,
    ragTestSearch,
    saveChunkHint,
    showError,
    suggestChunkHints,
  } = useAdminContext();

  const [step, setStep] = useState('diagnose');

  // diagnose
  const [searchData, setSearchData] = useState(null);
  const [searching, setSearching] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [keywordResults, setKeywordResults] = useState(null);
  const [expanded, setExpanded] = useState(null);

  // hint
  const [chunk, setChunk] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(false);

  // verified
  const [verification, setVerification] = useState(null);

  const topK = searchData?.top_k ?? 3;

  useEffect(() => {
    ragTestSearch(item.query)
      .then(setSearchData)
      .catch(err => showError(err.message))
      .finally(() => setSearching(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const runKeywordSearch = (e) => {
    e.preventDefault();
    if (!keyword.trim()) return;
    ragSearchChunks(keyword.trim())
      .then(data => setKeywordResults(data.results))
      .catch(err => showError(err.message));
  };

  const selectChunk = (c) => {
    // chunk จากการค้นหาข้อความไม่มีอันดับ — หาอันดับจากผลทดสอบค้นหาถ้ามี
    const ranked = searchData?.results.find(r => r.chunk_hash === c.chunk_hash && r.source === c.source);
    setChunk({ ...c, rank: ranked?.rank ?? null, in_chat_context: ranked?.in_chat_context ?? false });
    setStep('hint');
    const existing = c.hint_questions || [];
    setQuestions(existing.length ? existing : ['']);
    setSuggesting(true);
    suggestChunkHints(c, item.query)
      .then(data => {
        const merged = [...existing];
        (data.questions || []).forEach(q => {
          if (!merged.some(m => m.trim().toLowerCase() === q.trim().toLowerCase())) merged.push(q);
        });
        setQuestions(merged.length ? merged : ['']);
      })
      .catch(err => showError(err.message))
      .finally(() => setSuggesting(false));
  };

  const saveHint = async () => {
    const cleaned = questions.map(q => q.trim()).filter(Boolean);
    if (!cleaned.length) return;
    setSaving(true);
    setBusy(true);
    try {
      const data = await saveChunkHint(chunk, cleaned, item.id, item.query);
      setQuestions(data.questions);
      setVerification(data.verification);
      setStep('verified');
    } catch (err) {
      showError(err.message);
    } finally {
      setSaving(false);
      setBusy(false);
    }
  };

  const closeItem = async () => {
    setBusy(true);
    const ok = await handleResolveUnanswered(item.id, 'Resolved', {
      resolution_type: 'chunk_hint',
      note: `เอกสาร: ${chunk.source}${chunk.page ? ` หน้า ${chunk.page}` : ''}`,
    });
    setBusy(false);
    if (ok) onDone();
  };

  const cancelBtnClass = 'px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95';
  const primaryBtnClass = 'bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed';
  const labelClass = 'block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5';

  const chunkCard = (c, { showRank }) => {
    const id = `${c.source}|${c.chunk_hash}`;
    const isOpen = expanded === id;
    return (
      <div key={id} className="p-3.5 rounded-2xl border border-slate-200 dark:border-tuh-purple/20 bg-white/60 dark:bg-white/5 space-y-2">
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
          {showRank && (
            <span className="px-2 py-0.5 rounded-lg bg-slate-500/10 text-slate-600 dark:text-slate-300">อันดับ {c.rank}</span>
          )}
          {showRank && c.in_chat_context && (
            <span className="px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">ส่งให้บอทแล้ว</span>
          )}
          {c.hint_questions?.length > 0 && (
            <span className="px-2 py-0.5 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400">มีคำถามตัวอย่าง {c.hint_questions.length} ข้อ</span>
          )}
          <span className="text-slate-500 dark:text-slate-400 truncate">
            <i className="fa-solid fa-file-pdf mr-1 text-tuh-rose/70"></i>{c.source}{c.page ? ` · หน้า ${c.page}` : ''}
          </span>
        </div>
        <p className={`text-xs font-semibold text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-line ${isOpen ? '' : 'line-clamp-3'}`}>
          {c.content}
        </p>
        <div className="flex items-center justify-between gap-2">
          <button type="button" onClick={() => setExpanded(isOpen ? null : id)} className="text-[11px] font-bold text-slate-500 hover:text-tuh-rose transition">
            {isOpen ? 'ย่อ' : 'อ่านทั้งหมด'}
          </button>
          <button
            type="button"
            onClick={() => selectChunk(c)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-tuh-rose/10 text-tuh-rose hover:bg-tuh-rose/20 transition active:scale-95"
          >
            <i className="fa-solid fa-hand-pointer"></i> ส่วนนี้มีคำตอบ
          </button>
        </div>
      </div>
    );
  };

  if (step === 'diagnose') {
    return (
      <div className="space-y-4">
        <div className="p-4 rounded-2xl bg-sky-500/5 border border-sky-500/20 text-xs font-semibold text-slate-600 dark:text-slate-300 leading-relaxed">
          <div className="font-extrabold text-sky-600 dark:text-sky-400 flex items-center gap-1.5 mb-1">
            <i className="fa-solid fa-magnifying-glass"></i> ขั้นที่ 1: หาส่วนของเอกสารที่มีคำตอบ
          </div>
          ด้านล่างคือสิ่งที่ระบบค้นเจอเมื่อถามคำถามนี้ (เฉพาะ {topK} อันดับแรกเท่านั้นที่ถูกส่งให้บอทใช้ตอบ)
          — กด <b>"ส่วนนี้มีคำตอบ"</b> ที่ส่วนที่ถูกต้อง ถ้าไม่มีในรายการให้ค้นหาด้วยข้อความด้านล่าง
        </div>

        {searchData && !searchData.dense_enabled && (
          <div className="text-xs font-semibold text-amber-600 bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/20">
            ⚠️ ระบบค้นหาเชิงความหมาย (ChromaDB) ไม่ได้เปิดใช้งาน ผลค้นหาอาจแม่นน้อยกว่าปกติ — แจ้งทีมพัฒนา
          </div>
        )}

        <div className="space-y-2 max-h-[38vh] overflow-y-auto pr-1">
          {searching && (
            <div className="py-8 text-center text-sm text-slate-400 font-bold">
              <i className="fa-solid fa-spinner animate-spin mr-1.5"></i> กำลังทดสอบค้นหา...
            </div>
          )}
          {!searching && searchData?.results.length === 0 && (
            <div className="py-6 text-center text-sm text-slate-400 font-bold">ไม่พบผลการค้นหา</div>
          )}
          {!searching && searchData?.results.map(c => chunkCard(c, { showRank: true }))}
        </div>

        <form onSubmit={runKeywordSearch} className="space-y-2">
          <label className={labelClass}>ไม่เจอในรายการ? ค้นหาข้อความในเอกสาร</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="พิมพ์คำที่อยู่ในย่อหน้าที่มีคำตอบ เช่น ทบทวนนโยบาย"
              className="flex-1 min-w-0 tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
            />
            <button type="submit" className="px-4 rounded-2xl bg-slate-500/10 text-slate-600 dark:text-slate-300 font-bold text-sm hover:bg-slate-500/20 transition">
              ค้นหา
            </button>
          </div>
        </form>
        {keywordResults && (
          <div className="space-y-2 max-h-[30vh] overflow-y-auto pr-1">
            {keywordResults.length === 0
              ? <div className="text-xs text-slate-400 font-bold">ไม่พบข้อความนี้ในเอกสารที่ใช้งานอยู่</div>
              : keywordResults.map(c => chunkCard(c, { showRank: false }))}
          </div>
        )}

        <div className="flex flex-wrap justify-between items-center gap-3 pt-2">
          <button type="button" onClick={onBack} className={cancelBtnClass}>
            <i className="fa-solid fa-arrow-left mr-1.5"></i> ย้อนกลับ
          </button>
          <button type="button" onClick={onUseFaq} className="text-xs font-bold text-slate-500 hover:text-tuh-rose transition">
            ต้องการคำตอบตายตัวแทน? ใช้ FAQ
          </button>
        </div>
      </div>
    );
  }

  if (step === 'hint') {
    return (
      <div className="space-y-4">
        <div>
          <label className={labelClass}>ส่วนของเอกสารที่เลือก</label>
          <div className="p-3.5 rounded-2xl tuh-glass-2 space-y-1.5">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
              <i className="fa-solid fa-file-pdf mr-1 text-tuh-rose/70"></i>{chunk.source}{chunk.page ? ` · หน้า ${chunk.page}` : ''}
              {chunk.rank && ` · ตอนนี้อยู่อันดับ ${chunk.rank}`}
            </div>
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-line line-clamp-4">{chunk.content}</p>
          </div>
        </div>

        {chunk.in_chat_context && (
          <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs font-semibold text-slate-700 dark:text-slate-200 leading-relaxed">
            <div className="font-extrabold text-amber-600 dark:text-amber-400 mb-0.5">
              <i className="fa-solid fa-triangle-exclamation mr-1"></i> ระบบค้นเจอส่วนนี้และส่งให้บอทแล้ว
            </div>
            แปลว่าบอทได้รับข้อมูลแล้วแต่ยังตอบไม่ได้ — ปัญหาน่าจะอยู่ที่ขั้นตอนสร้างคำตอบ การเพิ่มคำถามตัวอย่างอาจไม่ช่วย
            ควรแจ้งทีมพัฒนา หรือ <button type="button" onClick={onUseFaq} className="underline font-bold text-tuh-rose">ใช้ FAQ</button> แทน
          </div>
        )}

        <div className="p-4 rounded-2xl bg-sky-500/5 border border-sky-500/20 text-xs font-semibold text-slate-600 dark:text-slate-300 leading-relaxed">
          <div className="font-extrabold text-sky-600 dark:text-sky-400 flex items-center gap-1.5 mb-1">
            <i className="fa-solid fa-lightbulb"></i> ขั้นที่ 2: ผูกคำถามตัวอย่างกับส่วนนี้
          </div>
          เขียนคำถามแบบที่คนทั่วไปน่าจะพิมพ์ถาม ระบบจะใช้คำถามเหล่านี้ช่วยค้นหาส่วนนี้ให้เจอ
          (คำตอบยังมาจากเนื้อหาเอกสารเดิมพร้อมลิงก์อ้างอิง) — AI เสนอให้แล้ว ตรวจและแก้ก่อนบันทึก
        </div>

        <div className="space-y-2">
          <label className={labelClass}>
            คำถามตัวอย่าง {suggesting && <span className="normal-case tracking-normal text-slate-400"><i className="fa-solid fa-spinner animate-spin mx-1"></i>AI กำลังเสนอ...</span>}
          </label>
          {questions.map((q, i) => (
            <div key={i} className="flex gap-2">
              <input
                type="text"
                value={q}
                maxLength={300}
                onChange={(e) => setQuestions(questions.map((x, j) => (j === i ? e.target.value : x)))}
                className="flex-1 min-w-0 tuh-glass-2 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
              />
              <button
                type="button"
                onClick={() => setQuestions(questions.length > 1 ? questions.filter((_, j) => j !== i) : [''])}
                className="px-3 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition"
                title="ลบคำถามนี้"
              >
                <i className="fa-solid fa-trash-can"></i>
              </button>
            </div>
          ))}
          {questions.length < 10 && (
            <button type="button" onClick={() => setQuestions([...questions, ''])} className="text-xs font-bold text-tuh-rose hover:underline">
              <i className="fa-solid fa-plus mr-1"></i> เพิ่มคำถาม
            </button>
          )}
        </div>

        <div className="flex justify-between gap-3 pt-2">
          <button type="button" onClick={() => setStep('diagnose')} disabled={saving} className={cancelBtnClass}>
            <i className="fa-solid fa-arrow-left mr-1.5"></i> เลือกส่วนอื่น
          </button>
          <button
            type="button"
            onClick={saveHint}
            disabled={saving || suggesting || !questions.some(q => q.trim())}
            className={primaryBtnClass}
          >
            <i className={`fa-solid ${saving ? 'fa-spinner animate-spin' : 'fa-graduation-cap'} mr-1.5`}></i> บันทึกและทดสอบ
          </button>
        </div>
      </div>
    );
  }

  // step === 'verified'
  const passed = verification?.in_chat_context;
  return (
    <div className="space-y-4">
      <div className={`p-4 rounded-2xl border text-sm font-semibold leading-relaxed ${passed
        ? 'bg-emerald-500/10 border-emerald-500/20 text-slate-700 dark:text-slate-200'
        : 'bg-amber-500/10 border-amber-500/20 text-slate-700 dark:text-slate-200'}`}
      >
        <div className={`font-extrabold mb-1 flex items-center gap-1.5 ${passed ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
          <i className={`fa-solid ${passed ? 'fa-circle-check' : 'fa-triangle-exclamation'}`}></i>
          {passed ? 'สอนสำเร็จ' : 'บันทึกแล้ว แต่ยังค้นไม่เจอพอ'}
        </div>
        {passed
          ? <>ทดสอบถามคำถามเดิมอีกครั้ง ระบบค้นเจอส่วนนี้เป็น <b>อันดับ {verification.rank}</b> และส่งให้บอทใช้ตอบแล้ว</>
          : <>ทดสอบถามคำถามเดิมอีกครั้ง ส่วนนี้{verification?.rank ? <> อยู่อันดับ <b>{verification.rank}</b></> : 'ยังไม่ติด 10 อันดับแรก'} แต่บอทใช้แค่ {verification?.top_k ?? topK} อันดับแรก
              — ลองเพิ่มคำถามที่ใช้คำเดียวกับผู้ใช้มากขึ้น หรือใช้ FAQ แทน</>}
      </div>
      <div>
        <label className={labelClass}>คำถามตัวอย่างที่บันทึก</label>
        <ul className="list-disc pl-5 text-sm font-semibold text-slate-700 dark:text-slate-200 space-y-0.5">
          {questions.map((q, i) => <li key={i}>{q}</li>)}
        </ul>
      </div>
      <div className="flex flex-wrap justify-end gap-3 pt-2">
        {!passed && (
          <>
            <button type="button" onClick={onUseFaq} className={cancelBtnClass}>ใช้ FAQ แทน</button>
            <button type="button" onClick={() => setStep('hint')} className={cancelBtnClass}>แก้คำถาม</button>
          </>
        )}
        <button type="button" onClick={closeItem} className={primaryBtnClass}>
          <i className="fa-solid fa-check mr-1.5"></i> ปิดรายการ
        </button>
      </div>
    </div>
  );
}
