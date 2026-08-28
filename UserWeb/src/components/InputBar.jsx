import React from 'react';

export const InputBar = ({
  isActiveSessionLatest,
  showFaqs,
  setShowFaqs,
  faqsList,
  isTyping,
  inputValue,
  setInputValue,
  handleSendMessage,
  handleStopGeneration,
  inputRef
}) => {
  return (
    <div className="p-3 border-t border-slate-200/60 dark:border-tuh-purple/15 bg-white/50 dark:bg-[#1B2062]/50 shrink-0">
      {isActiveSessionLatest ? (
        <div className="flex flex-col w-full">
          {/* ปุ่มเปิดปิดคำถามที่พบบ่อย (FAQs) */}
          <div className="flex items-center mb-2">
            <button
              onClick={() => setShowFaqs(!showFaqs)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-[#07010f] border border-slate-200 dark:border-tuh-purple/20 text-tuh-indigo/70 dark:text-slate-300 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-indigo/60 transition active:scale-95 shadow-sm"
            >
              <i className="fa-solid fa-circle-question text-tuh-rose dark:text-tuh-pink"></i>
              <span>คำถามที่พบบ่อย (FAQs)</span>
              <i className={`fa-solid ${showFaqs ? 'fa-chevron-down' : 'fa-chevron-up'} text-[10px] ml-1`}></i>
            </button>
          </div>

          {/* รายการคำถามที่พบบ่อย (FAQs List) */}
          {showFaqs && faqsList.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3 max-h-40 overflow-y-auto custom-scrollbar p-1.5 bg-slate-50/50 dark:bg-[#07010f]/30 rounded-xl border border-slate-200/40 dark:border-white/5 animate-slide-in">
              {faqsList.map(faq => (
                <button
                  key={faq.id}
                  onClick={() => handleSendMessage(faq.question)}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-xl bg-white dark:bg-[#1B2062]/55 hover:bg-tuh-rose/10 hover:text-tuh-rose dark:hover:bg-tuh-rose/25 dark:hover:text-white border border-slate-200/60 dark:border-white/5 shadow-sm transition active:scale-[0.97] w-full text-left"
                >
                  <i className={`fa-solid ${faq.icon || 'fa-lightbulb'} text-tuh-rose text-[11px] shrink-0`}></i>
                  <span className="leading-snug">{faq.question}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2.5 w-full">
            <textarea
              ref={inputRef}
              value={inputValue}
              disabled={isTyping}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(inputValue);
                }
              }}
              rows={1}
              placeholder={isTyping ? "กำลังประมวลผล..." : "พิมพ์ข้อความของคุณที่นี่..."}
              className="floating-textarea flex-1 py-3 px-4 rounded-xl bg-slate-50 dark:bg-[#07010f] border border-slate-250 dark:border-tuh-purple/25 text-tuh-navy dark:text-white placeholder-slate-400 dark:placeholder-white/40 focus:outline-none text-xs md:text-sm resize-none overflow-y-auto leading-normal focus:ring-2 focus:ring-tuh-rose/30 dark:focus:ring-tuh-rose/50 transition-all duration-300"
            />

            {isTyping ? (
              <button
                onClick={handleStopGeneration}
                className="h-[46px] w-[46px] rounded-xl bg-gradient-to-r from-red-500 to-rose-600 text-white flex items-center justify-center hover:scale-[1.05] active:scale-[0.98] transition-all shrink-0 shadow-md hover:shadow-red-500/20"
                title="หยุดหาคำตอบ"
              >
                <i className="fa-solid fa-stop text-sm"></i>
              </button>
            ) : (
              <button
                onClick={() => handleSendMessage(inputValue)}
                disabled={isTyping}
                className="h-[46px] w-[46px] rounded-xl bg-tuh-gradient-2 text-white flex items-center justify-center hover:scale-[1.05] active:scale-[0.98] transition-all shrink-0 shadow-md hover:shadow-tuh-rose/20"
                title="ส่งข้อความ"
              >
                <i className="fa-solid fa-paper-plane text-sm"></i>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="w-full flex items-center justify-center p-3 rounded-xl bg-slate-100/80 dark:bg-tuh-navy/40 border border-slate-200 dark:border-white/5 text-slate-500 dark:text-slate-400 font-bold text-center text-xs md:text-sm select-none gap-2">
          <i className="fa-solid fa-lock text-tuh-rose text-sm"></i>
          <span>บทสนทนานี้หมดเวลาส่งข้อความแล้ว สามารถดูประวัติการสนทนาได้อย่างเดียว</span>
        </div>
      )}
    </div>
  );
};

export default InputBar;
