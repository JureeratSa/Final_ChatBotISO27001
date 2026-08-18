/**
 * TUH Chatbot AI v2 — Input Bar Component
 * คง UX เดิม: Enter to send, Shift+Enter for newline, voice input placeholder
 */
import React, { useRef, useEffect } from 'react';

const InputBar = ({ onSend, isLoading, isDarkMode }) => {
  const textareaRef = useRef(null);
  const [value, setValue] = React.useState('');

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  };

  useEffect(() => { autoResize(); }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  return (
    <div className="p-4">
      <div className="glass-panel rounded-2xl px-4 py-3 flex items-end gap-3">
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="พิมพ์คำถามที่ต้องการสอบถาม..."
          rows={1}
          className="flex-1 bg-transparent resize-none focus:outline-none text-sm leading-relaxed text-slate-800 dark:text-slate-100 placeholder-slate-400"
          disabled={isLoading}
          style={{ maxHeight: '140px', overflowY: 'auto' }}
        />
        <button
          id="send-button"
          onClick={handleSend}
          disabled={isLoading || !value.trim()}
          className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 
            ${value.trim() && !isLoading
              ? 'bg-tuh-gradient-1 text-white shadow-md hover:shadow-lg hover:scale-105 active:scale-95'
              : 'bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
            }`}
        >
          {isLoading ? (
            <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          ) : (
            <i className="fas fa-paper-plane text-sm" />
          )}
        </button>
      </div>
      <p className="text-xs text-slate-400 text-center mt-2">
        กด <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-xs">Enter</kbd> เพื่อส่ง
        {' '}• <kbd className="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-xs">Shift+Enter</kbd> เพื่อขึ้นบรรทัดใหม่
      </p>
    </div>
  );
};

export default InputBar;
