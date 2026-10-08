import { useEffect, useState } from 'react';
import { useAdminContext } from '../../context/AdminContext';
import { IGNORE_REASONS } from './unansweredLabels';

/**
 * ResolveUnansweredModal — modal ปิดรายการคำถามที่บอทตอบไม่ได้ในหน้า Logs
 *
 * mode="resolve" (ปุ่ม "แก้ไข") แบ่งเป็นขั้นตอน:
 *   ask       → ถามว่าข้อมูลนี้มีในเอกสาร PDF แล้วหรือยัง
 *   in_pdf    → มีแล้วแต่บอทหาไม่เจอ: แนะนำวิธีสอน + คำค้นจาก AI แล้วลงทะเบียน Custom FAQ
 *   upload    → ยังไม่มี: อัปโหลด PDF ใหม่ (ฟอร์มเดียวกับหน้าจัดการเอกสาร)
 *   uploaded  → อัปโหลดแล้ว: เตือนให้ไปอนุมัติ pipeline ในหน้าจัดการเอกสาร
 * mode="ignore" (ปุ่ม "ไม่แก้ไข") → เลือกเหตุผล + หมายเหตุ แล้วปิดรายการเป็น Ignored
 *
 * หมายเหตุ: ไม่มีทางเลือก "แก้ส่วนย่อย (chunk)" ใน flow นี้ เพราะการบันทึก chunk ในหน้าเอกสาร
 * เขียนแค่ไฟล์ .chunks.json แต่ยังไม่ถูกนำเข้า index ที่บอทใช้ค้นจริง
 */
export default function ResolveUnansweredModal({ item, mode, onClose }) {
  const {
    analyzeUnansweredQuery,
    handleResolveUnanswered,
    handleTabClick,
    saveCustomFaq,
    uploadFile,
    uploadProgress,
    uploading,
  } = useAdminContext();

  const [step, setStep] = useState(mode === 'ignore' ? 'ignore' : 'ask');
  const [submitting, setSubmitting] = useState(false);

  // in_pdf
  const [faqQuestion, setFaqQuestion] = useState(item.query);
  const [faqAnswer, setFaqAnswer] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // upload
  const [file, setFile] = useState(null);
  const [displayName, setDisplayName] = useState('');
  const [excludePages, setExcludePages] = useState('');

  // ignore
  const [ignoreReason, setIgnoreReason] = useState('');
  const [note, setNote] = useState('');

  useEffect(() => {
    if (step !== 'in_pdf' || analysis || analysisLoading) return;
    setAnalysisLoading(true);
    analyzeUnansweredQuery(item.query).then(result => {
      setAnalysis(result || { is_valid_query: true, suggested_keywords: [] });
      setAnalysisLoading(false);
    });
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  const close = () => {
    if (!submitting) onClose();
  };

  const submitFaq = async (e) => {
    e.preventDefault();
    if (!faqQuestion.trim() || !faqAnswer.trim()) return;
    setSubmitting(true);
    const ok = await saveCustomFaq(faqQuestion, faqAnswer);
    if (ok) {
      await handleResolveUnanswered(item.id, 'Resolved', {
        resolution_type: 'custom_faq',
        note: faqQuestion.trim() !== item.query.trim() ? `คำถาม FAQ: ${faqQuestion.trim()}` : undefined,
      });
      setSubmitting(false);
      onClose();
      return;
    }
    setSubmitting(false);
  };

  const submitUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    const name = displayName.trim() || file.name;
    const ok = await uploadFile(file, excludePages, name);
    if (ok) {
      await handleResolveUnanswered(item.id, 'Resolved', {
        resolution_type: 'document_upload',
        note: `อัปโหลดเอกสาร: ${name}`,
      });
      setStep('uploaded');
    }
    setSubmitting(false);
  };

  const submitIgnore = async (e) => {
    e.preventDefault();
    if (!ignoreReason) return;
    setSubmitting(true);
    const ok = await handleResolveUnanswered(item.id, 'Ignored', {
      ignore_reason: ignoreReason,
      note: note.trim() || undefined,
    });
    setSubmitting(false);
    if (ok) onClose();
  };

  const goToDocuments = () => {
    onClose();
    handleTabClick('documents');
  };

  const title = {
    ask: 'แก้ไขคำถามที่บอทตอบไม่ได้',
    in_pdf: 'สอนคำตอบให้บอท',
    upload: 'อัปโหลดเอกสารใหม่',
    uploaded: 'อัปโหลดเอกสารแล้ว',
    ignore: 'ไม่แก้ไขคำถามนี้',
  }[step];

  const icon = {
    ask: 'fa-screwdriver-wrench',
    in_pdf: 'fa-feather',
    upload: 'fa-file-circle-plus',
    uploaded: 'fa-circle-check',
    ignore: 'fa-ban',
  }[step];

  const inputClass = 'w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-tuh-navy dark:text-white';
  const labelClass = 'block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5';
  const cancelBtnClass = 'px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95';
  const primaryBtnClass = 'bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed';
  const backBtn = (
    <button type="button" onClick={() => setStep('ask')} disabled={submitting} className={cancelBtnClass}>
      <i className="fa-solid fa-arrow-left mr-1.5"></i> ย้อนกลับ
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto tuh-glass-1 tuh-border-glass-strong rounded-3xl shadow-2xl animate-slide-in">
        <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
          <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
            <i className={`fa-solid ${icon} text-tuh-rose`}></i> {title}
          </h3>
          <button
            onClick={close}
            className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className={labelClass}>คำถามจากผู้ใช้</label>
            <div className="p-4 tuh-glass-2 rounded-2xl font-bold">{item.query}</div>
          </div>

          {step === 'ask' && (
            <>
              <p className="text-sm font-bold text-slate-700 dark:text-slate-200">
                ข้อมูลที่ใช้ตอบคำถามนี้ มีอยู่ในเอกสาร PDF ที่อัปโหลดไว้แล้วหรือยัง?
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setStep('in_pdf')}
                  className="p-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10 text-left transition active:scale-[0.98]"
                >
                  <div className="font-extrabold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                    <i className="fa-solid fa-file-circle-check"></i> มีในเอกสารแล้ว
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
                    แต่บอทหาไม่เจอ → สอนคำตอบให้บอท
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setStep('upload')}
                  className="p-4 rounded-2xl border border-tuh-rose/30 bg-tuh-rose/5 hover:bg-tuh-rose/10 text-left transition active:scale-[0.98]"
                >
                  <div className="font-extrabold text-tuh-rose flex items-center gap-2">
                    <i className="fa-solid fa-file-circle-plus"></i> ยังไม่มี
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
                    อัปโหลดเอกสาร PDF ที่มีคำตอบเพิ่ม
                  </div>
                </button>
              </div>
              <div className="flex justify-end pt-2">
                <button type="button" onClick={close} className={cancelBtnClass}>ยกเลิก</button>
              </div>
            </>
          )}

          {step === 'in_pdf' && (
            <form onSubmit={submitFaq} className="space-y-4">
              <div className="p-4 rounded-2xl bg-sky-500/5 border border-sky-500/20 text-xs font-semibold text-slate-600 dark:text-slate-300 leading-relaxed space-y-1.5">
                <div className="font-extrabold text-sky-600 dark:text-sky-400 flex items-center gap-1.5">
                  <i className="fa-solid fa-lightbulb"></i> วิธีสอนบอท
                </div>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>เปิดเอกสาร PDF ที่มีคำตอบ แล้วสรุปคำตอบให้สั้น กระชับ ตรงประเด็น</li>
                  <li>
                    ตัด "คำถาม FAQ" ให้เหลือแค่แก่นของคำถาม — บอทจะตอบด้วย FAQ นี้เมื่อ
                    <span className="text-tuh-rose"> ข้อความคำถาม FAQ ปรากฏอยู่ในคำถามของผู้ใช้</span>
                    {' '}เช่น "ISMS คืออะไร" จะจับได้ทั้ง "ระบบ ISMS คืออะไร" และ "อยากรู้ว่า ISMS คืออะไรครับ"
                  </li>
                  <li>ระบุชื่อเอกสาร/หน้าอ้างอิงท้ายคำตอบ เพื่อให้ผู้ใช้ตามไปอ่านต่อได้</li>
                </ol>
              </div>

              <div className="p-4 rounded-2xl border border-dashed border-tuh-purple/20 bg-slate-50 dark:bg-[#100220]/25 space-y-2">
                <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <i className="fa-solid fa-wand-magic-sparkles text-tuh-rose"></i> คำค้นแนะนำโดย AI
                </span>
                {analysisLoading && (
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <i className="fa-solid fa-spinner animate-spin text-[10px]"></i> กำลังวิเคราะห์...
                  </div>
                )}
                {analysis && analysis.is_valid_query === false && (
                  <div className="text-xs font-semibold text-rose-500 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
                    ⚠️ AI ประเมินว่าข้อความนี้อาจเป็นคำทักทายหรือข้อความขยะ — พิจารณาเลือก "ไม่แก้ไข" แทน
                  </div>
                )}
                {analysis && analysis.is_valid_query !== false && (
                  analysis.suggested_keywords?.length ? (
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.suggested_keywords.map((kw, i) => (
                        <span key={i} className="px-2.5 py-1 text-xs font-bold rounded-lg bg-tuh-rose/10 text-tuh-rose">{kw}</span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 font-semibold">ไม่มีคำแนะนำ</div>
                  )
                )}
              </div>

              <div>
                <label className={labelClass}>คำถาม FAQ (ตัดให้เหลือแก่นของคำถาม)</label>
                <input
                  type="text"
                  required
                  value={faqQuestion}
                  onChange={(e) => setFaqQuestion(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>คำตอบ (บอทจะตอบข้อความนี้ตรงๆ ทันที)</label>
                <textarea
                  rows="4"
                  required
                  placeholder="เขียนคำตอบที่สั้น กระชับ ตรงประเด็น พร้อมอ้างอิงเอกสาร..."
                  value={faqAnswer}
                  onChange={(e) => setFaqAnswer(e.target.value)}
                  className={`${inputClass} text-sm leading-relaxed`}
                ></textarea>
              </div>
              <div className="flex justify-between gap-3 pt-2">
                {backBtn}
                <button type="submit" disabled={submitting} className={primaryBtnClass}>
                  <i className={`fa-solid ${submitting ? 'fa-spinner animate-spin' : 'fa-save'} mr-1.5`}></i> ลงทะเบียนคำตอบและปิดรายการ
                </button>
              </div>
            </form>
          )}

          {step === 'upload' && (
            <form onSubmit={submitUpload} className="space-y-4">
              {uploading ? (
                <div className="space-y-3 py-4 text-center">
                  <div className="w-10 h-10 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin mx-auto"></div>
                  <div className="font-bold text-sm">กำลังอัปโหลดเอกสาร PDF... ({uploadProgress}%)</div>
                  <div className="w-full bg-slate-100 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                    <div className="bg-tuh-rose h-full rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <label className={labelClass}>ไฟล์ PDF</label>
                    <input
                      type="file"
                      accept=".pdf"
                      required
                      onChange={(e) => {
                        const f = e.target.files && e.target.files[0];
                        setFile(f || null);
                        if (f) setDisplayName(f.name);
                      }}
                      className="w-full text-sm font-semibold text-slate-600 dark:text-slate-300 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:font-bold file:bg-tuh-rose file:text-white file:cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                      ชื่อที่จะให้แสดงในคอลัมน์ชื่อไฟล์ ตารางแฟ้มเอกสารทั้งหมด
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="กรอกชื่อที่จะให้แสดงในตาราง..."
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                      ระบุหมายเลขหน้าที่ต้องการ "ละเว้น" (ถ้ามี)
                    </label>
                    <input
                      type="text"
                      placeholder="ระบุเลขหน้า เช่น 12, 13, 14, 18 (คั่นด้วยจุลภาค ,) หรือปล่อยว่างไว้"
                      value={excludePages}
                      onChange={(e) => setExcludePages(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                </>
              )}
              <div className="flex justify-between gap-3 pt-2">
                {backBtn}
                <button type="submit" disabled={submitting || !file} className={primaryBtnClass}>
                  <i className="fa-solid fa-cloud-arrow-up mr-1.5"></i> อัปโหลดและปิดรายการ
                </button>
              </div>
            </form>
          )}

          {step === 'uploaded' && (
            <>
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-sm font-semibold text-slate-700 dark:text-slate-200 leading-relaxed">
                <div className="font-extrabold text-amber-600 dark:text-amber-400 flex items-center gap-1.5 mb-1">
                  <i className="fa-solid fa-triangle-exclamation"></i> อีก 1 ขั้นตอน
                </div>
                เอกสารยังไม่ถูกนำไปให้บอทใช้จนกว่าจะตรวจและ <b>อนุมัติครบทุกขั้นตอน</b> (คำดิบ → ข้อความหลังคลีน → ส่วนย่อย)
                ในหน้าจัดการเอกสาร — ถ้ามีผู้ถามคำถามนี้แล้วบอทยังตอบไม่ได้ รายการจะกลับมาเป็น "รอการตรวจเช็ค" อัตโนมัติ
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={close} className={cancelBtnClass}>ปิด</button>
                <button type="button" onClick={goToDocuments} className={primaryBtnClass}>
                  <i className="fa-solid fa-file-pdf mr-1.5"></i> ไปหน้าจัดการเอกสาร
                </button>
              </div>
            </>
          )}

          {step === 'ignore' && (
            <form onSubmit={submitIgnore} className="space-y-4">
              <div>
                <label className={labelClass}>เหตุผลที่ไม่แก้ไข</label>
                <div className="space-y-2">
                  {IGNORE_REASONS.map(r => (
                    <label
                      key={r.value}
                      className={`flex items-center gap-2.5 p-3 rounded-2xl border cursor-pointer transition text-sm font-bold ${ignoreReason === r.value
                        ? 'border-tuh-rose bg-tuh-rose/5 text-tuh-navy dark:text-white'
                        : 'border-slate-200 dark:border-tuh-purple/20 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                        }`}
                    >
                      <input
                        type="radio"
                        name="ignore-reason"
                        value={r.value}
                        checked={ignoreReason === r.value}
                        onChange={() => setIgnoreReason(r.value)}
                        className="accent-rose-500"
                      />
                      {r.label}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className={labelClass}>หมายเหตุ {ignoreReason === 'other' ? '(จำเป็น)' : '(ถ้ามี)'}</label>
                <textarea
                  rows="3"
                  maxLength={1000}
                  required={ignoreReason === 'other'}
                  placeholder="รายละเอียดเพิ่มเติม เผื่อนำไปใช้ต่อ..."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className={`${inputClass} text-sm`}
                ></textarea>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={close} className={cancelBtnClass}>ยกเลิก</button>
                <button type="submit" disabled={submitting || !ignoreReason} className={primaryBtnClass}>
                  <i className={`fa-solid ${submitting ? 'fa-spinner animate-spin' : 'fa-ban'} mr-1.5`}></i> ยืนยันไม่แก้ไข
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
