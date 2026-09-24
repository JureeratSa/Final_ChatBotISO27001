/**
 * TUH Chatbot AI — MessageBubble Component
 * ฟองข้อความแสดงผลการสนทนา (User / Bot Message):
 * 1. แสดงรูปอวาตาร์ (ไอคอน User หรือ รูปน้องขาหมูตาม Theme)
 * 2. แปลง Markdown สำหรับข้อความแชทอย่างปลอดภัย (Safe parseMarkdown ป้องกัน XSS)
 * 3. แสดงรายการเอกสารอ้างอิง (PDF Citations พร้อมเลขหน้า) หากบอทค้นเจอจากฐานข้อมูล RAG
 * 4. ฝั่งบอท: ปุ่มถูกใจ (Like), ไม่ถูกใจ (Dislike -> เปิด Modal), คัดลอก (Copy), และ Timestamp
 * 5. ฝั่งผู้ใช้: Timestamp และปุ่มคัดลอกข้อความกลับเข้าช่องพิมพ์ (Re-ask icon)
 */
import React from 'react';

export const MessageBubble = ({
  msg,
  isDarkMode,
  copiedId,
  isTyping,
  currentBotAvatar,
  handleLikeMessage,
  handleCopyMessage,
  setInputValue,
  parseMarkdown,
  apiUrl
}) => {
  const isBot = msg.sender === 'bot';
  const citations = isBot && Array.isArray(msg.citations) ? msg.citations : [];

  return (
    <div
      className={`flex gap-2 max-w-[60%] ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'} animate-slide-in`}
    >
      {/* 1. ไอคอนอวาตาร์ของผู้ส่ง (Bot หรือ User) */}
      {isBot ? (
        <img
          src={currentBotAvatar}
          alt="Bot Icon"
          className={`w-7 h-7 rounded-lg object-cover shrink-0 ${!isDarkMode ? 'object-top' : ''}`}
        />
      ) : (
        <div className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] shrink-0 shadow-sm text-white bg-tuh-gradient-1">
          <i className="fa-solid fa-user"></i>
        </div>
      )}

      {/* 2. ฟองคำพูดแสดงเนื้อหาข้อความ */}
      <div className="space-y-1 min-w-0">
        <div className={`text-base leading-relaxed break-words ${isBot
          ? 'p-3 rounded-2xl shadow-sm bg-slate-100 dark:bg-[#07010f] border border-slate-200/60 dark:border-tuh-purple/20 text-tuh-navy dark:text-white rounded-tl-sm'
          : 'p-3 rounded-2xl shadow-md bg-[#f8bbd0] text-black dark:bg-[#ad1457] dark:text-white rounded-tr-sm'
          }`}>
          {parseMarkdown(msg.text)}
        </div>

        {/* 3. ส่วนแสดงรายการเอกสารอ้างอิง (Citations) */}
        {isBot && citations.length > 0 && (
          <div className="flex flex-wrap gap-1 px-0.5">
            {citations.map((c, i) => (
              <a
                key={`${c.source}-${i}`}
                href={`${apiUrl}${c.url}`}
                target="_blank"
                rel="noopener noreferrer"
                title={`เปิดดู ${c.display_name || c.source}${c.pages && c.pages.length ? ` หน้า ${c.pages[0]}` : ''}`}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium bg-tuh-rose/10 text-tuh-rose hover:bg-tuh-rose/20 dark:bg-tuh-pink/10 dark:text-tuh-pink dark:hover:bg-tuh-pink/20 transition-colors"
              >
                <i className="fa-solid fa-file-pdf"></i>
                <span className="truncate max-w-[160px]">{c.display_name || c.source}</span>
                {c.pages && c.pages.length > 0 && (
                  <span className="opacity-70">หน้า {c.pages[0]}</span>
                )}
              </a>
            ))}
          </div>
        )}

        {/* 4. แถบเครื่องมือใต้ข้อความ (Like / Dislike / Copy / Timestamp) */}
        {isBot ? (
          <div className="flex items-center gap-1.5 mt-1 px-0.5">
            {/* ปุ่มถูกใจคำตอบ */}
            <button
              onClick={() => handleLikeMessage(msg.id, 'like')}
              className={`p-1 rounded-md text-[13px] transition-all ${msg.liked ? 'text-emerald-500 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-500 dark:hover:text-emerald-400'}`}
              title="ถูกใจคำตอบนี้"
            >
              <i className={`fa-thumbs-up ${msg.liked ? 'fa-solid' : 'fa-regular'}`}></i>
            </button>
            {/* ปุ่มไม่ถูกใจคำตอบ (เปิด Modal แจ้งเหตุผล) */}
            <button
              onClick={() => handleLikeMessage(msg.id, 'dislike')}
              className={`p-1 rounded-md text-[13px] transition-all ${msg.disliked ? 'text-red-500 bg-red-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-red-500 dark:hover:text-red-400'}`}
              title="ไม่พึงพอใจคำตอบนี้"
            >
              <i className={`fa-thumbs-down ${msg.disliked ? 'fa-solid' : 'fa-regular'}`}></i>
            </button>
            {/* ปุ่มคัดลอกข้อความ */}
            <button
              onClick={() => handleCopyMessage(msg.text, msg.id)}
              className={`p-1 rounded-md text-[13px] transition-all flex items-center gap-0.5 ${copiedId === msg.id ? 'text-emerald-600 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-600 dark:hover:text-emerald-400'}`}
              title="คัดลอกข้อความ"
            >
              <i className={`fa-solid ${copiedId === msg.id ? 'fa-check' : 'fa-copy'}`}></i>
            </button>
            <span className="text-[12px] text-tuh-indigo/25 dark:text-slate-400/30">•</span>
            <span className="text-[13px] text-tuh-indigo/40 dark:text-tuh-pink/40 font-medium">{msg.timestamp}</span>
          </div>
        ) : (
          <div className="flex items-center justify-end gap-1.5 mt-1 px-0.5">
            <span className="text-[13px] text-tuh-indigo/40 dark:text-tuh-pink/40 font-medium">{msg.timestamp}</span>
            <span className="text-[12px] text-tuh-indigo/25 dark:text-slate-400/30">•</span>
            {/* ปุ่มดึงคำถามเดิมกลับมาใส่ในช่องพิมพ์ */}
            <button
              onClick={() => {
                setInputValue(msg.text);
                const textarea = document.querySelector('.floating-textarea');
                if (textarea) textarea.focus();
              }}
              disabled={isTyping}
              className="p-0.5 rounded-md text-[13px] text-tuh-indigo/35 dark:text-slate-400/50 hover:text-orange-500 dark:hover:text-orange-400"
              title="นำคำถามนี้กลับมาพิมพ์ใหม่"
            >
              <i className="fa-solid fa-arrow-rotate-left text-[12px]"></i>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;

