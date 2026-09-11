import { useAdminContext } from '../context/AdminContext';

/**
 * SettingsPage — แท็บ "ตั้งค่าระบบ AI" (เฉพาะ System Administrator) ปรับพารามิเตอร์โมเดล
 * และข้อความ/System Prompt ของแชทบอท — แยกออกมาจาก App.jsx เดิม
 */
export default function SettingsPage() {
  const {
    handleSaveSettings,
    setSettings,
    settings,
  } = useAdminContext();

  return (
    <form onSubmit={handleSaveSettings} className="space-y-6 animate-slide-in">
      <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm space-y-6">
        <h3 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-tuh-purple/20 pb-4"><i className="fa-solid fa-sliders text-tuh-rose"></i> การตั้งค่าโมเดล AI และพารามิเตอร์</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-bold mb-2">ค่าความสุ่มคำตอบ (Temperature): {settings.temperature}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
              className="w-full accent-tuh-rose cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 font-bold mt-1">
              <span>0.0 (ตอบแม่นยำสูงอิงเอกสาร)</span>
              <span>1.0 (อิสระและมีความคิดสร้างสรรค์)</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">จำนวนข้อความดึงจาก Vector (Top K): {settings.top_k} Chunks</label>
            <input
              type="range"
              min="1"
              max="6"
              step="1"
              value={settings.top_k}
              onChange={(e) => setSettings({ ...settings, top_k: parseInt(e.target.value, 10) })}
              className="w-full accent-tuh-rose cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 font-bold mt-1">
              <span>1 Chunk (ดึงกระชับที่สุด)</span>
              <span>6 Chunks (ดึงข้อมูลได้ละเอียดครอบคลุม)</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">ความยาวผลลัพธ์คำตอบสูงสุด (Max Tokens): {settings.max_tokens} Tokens</label>
            <input
              type="range"
              min="200"
              max="4000"
              step="100"
              value={settings.max_tokens || 400}
              onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value, 10) })}
              className="w-full accent-tuh-rose cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 font-bold mt-1">
              <span>200 (คำตอบสั้นและเร็ว)</span>
              <span>4000 (คำตอบยาวละเอียด)</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">เทคโนโลยีการทำ Embedding (Embedding Technology)</label>
            <div className="w-full bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 font-semibold text-slate-500 dark:text-slate-400 select-none">
              ChromaDB (BAAI/bge-m3) & BM25 Hybrid Search (รันบนเครื่อง)
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold mt-1">
              ระบบประมวลผลและค้นหาข้อมูลแบบไฮบริด (ChromaDB & BM25) เพื่อความเร็วสูงสุดและไม่ต้องพึ่งพาคลาวด์
            </div>
          </div>
        </div>
      </div>

      <div className="tuh-glass-1 rounded-3xl p-6 shadow-sm space-y-6">
        <h3 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-tuh-purple/20 pb-4"><i className="fa-solid fa-message text-tuh-rose"></i> การปรับแต่งประโยคและ System Prompt</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold mb-2">คำกล่าวต้อนรับแรกเริ่มแชท (Welcome Message)</label>
            <textarea
              rows="3"
              value={settings.welcome_message}
              onChange={(e) => setSettings({ ...settings, welcome_message: e.target.value })}
              placeholder="เขียนประโยคตอบรับครั้งแรกเมื่อเปิดใช้งานแชทบอท..."
              className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
            ></textarea>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">คำทักทายเริ่มต้นบทสนทนาใหม่ในแชท (Chat Greeting)</label>
            <textarea
              rows="3"
              value={settings.chat_greeting}
              onChange={(e) => setSettings({ ...settings, chat_greeting: e.target.value })}
              placeholder="เขียนประโยคทักทายครั้งแรกในห้องแชท..."
              className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
            ></textarea>
          </div>

          <div>
            <label className="block text-sm font-bold mb-2">คำสั่งระบบควบคุมพฤติกรรมบอท (System Prompt)</label>
            <textarea
              rows="12"
              value={settings.system_prompt}
              onChange={(e) => setSettings({ ...settings, system_prompt: e.target.value })}
              placeholder="เช่น 'คุณคือระบบตอบคำถามสำหรับโรงพยาบาลธรรมศาสตร์...'"
              className="w-full tuh-glass-2 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm leading-relaxed"
            ></textarea>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          className="bg-tuh-gradient-2 text-white hover:shadow-lg hover:scale-[1.01] transition font-bold py-3 px-8 rounded-2xl active:scale-[0.99] flex items-center gap-2"
        >
          <i className="fa-solid fa-floppy-disk animate-pulse"></i> บันทึกการตั้งค่าทั้งหมด
        </button>
      </div>
    </form>
  );
}
