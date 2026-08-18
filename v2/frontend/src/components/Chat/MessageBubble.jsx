/**
 * TUH Chatbot AI v2 — Message Bubble Component
 * คง UI/UX เดิมทุกประการ: glassmorphism, animations, feedback buttons, citations
 */
import React, { useState } from 'react';

// ─── HTML Content Renderer (คง logic เดิม) ───────────────────────────────────
const HtmlContent = ({ html }) => (
  <div
    className="html-content"
    dangerouslySetInnerHTML={{ __html: html }}
  />
);

// ─── Citation Block ────────────────────────────────────────────────────────────
const CitationBlock = ({ citations }) => {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-white/10">
      <p className="text-xs font-semibold text-slate-400 mb-1.5">📎 เอกสารอ้างอิง</p>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => (
          <a
            key={i}
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors border border-blue-500/20"
          >
            📄 {c.display_name || c.source}
            {c.pages?.length > 0 && ` หน้า ${c.pages.join(', ')}`}
          </a>
        ))}
      </div>
    </div>
  );
};

// ─── Form Links Block ──────────────────────────────────────────────────────────
const FormLinksBlock = ({ formLinks }) => {
  if (!formLinks || formLinks.length === 0) return null;
  return (
    <div className="mt-2 pt-2 border-t border-white/10">
      <p className="text-xs font-semibold text-slate-400 mb-1.5">🔗 แบบฟอร์มที่เกี่ยวข้อง</p>
      <div className="flex flex-wrap gap-1.5">
        {formLinks.map((f, i) => (
          <a
            key={i}
            href={f.download_link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors border border-green-500/20"
          >
            📋 {f.name}
          </a>
        ))}
      </div>
    </div>
  );
};

// ─── Message Bubble ────────────────────────────────────────────────────────────
const MessageBubble = ({ message, botAvatar, onFeedback, isDarkMode }) => {
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState('');

  const isBot = message.sender === 'bot';

  const handleFeedback = (rating) => {
    if (message.feedback) return; // Already rated
    if (rating === 'dislike') {
      setShowFeedbackInput(true);
    } else {
      onFeedback?.(message.id, message.historyId, rating);
    }
  };

  const submitFeedback = () => {
    onFeedback?.(message.id, message.historyId, 'dislike', feedbackComment);
    setShowFeedbackInput(false);
  };

  if (!isBot) {
    // User message
    return (
      <div className="flex justify-end items-end gap-2 animate-slide-in">
        <div className="max-w-[75%]">
          <div className="bg-tuh-gradient-1 text-white px-4 py-3 rounded-2xl rounded-br-sm shadow-md">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
          </div>
          <p className="text-xs text-slate-400 mt-1 text-right">{message.timestamp}</p>
        </div>
      </div>
    );
  }

  // Bot message
  return (
    <div className="flex items-start gap-3 animate-slide-in">
      {/* Bot Avatar */}
      <div className="flex-shrink-0 w-9 h-9 rounded-full overflow-hidden border-2 border-blue-400/30 shadow-md">
        <img src={botAvatar} alt="Bot" className="w-full h-full object-cover" />
      </div>

      <div className="max-w-[80%]">
        {/* Message bubble */}
        <div className="glass-panel px-4 py-3 rounded-2xl rounded-tl-sm text-slate-800 dark:text-slate-100">
          <HtmlContent html={message.text} />
          <CitationBlock citations={message.citations} />
          <FormLinksBlock formLinks={message.formLinks} />
        </div>

        {/* Timestamp + Feedback */}
        <div className="flex items-center gap-2 mt-1.5">
          <p className="text-xs text-slate-400">{message.timestamp}</p>

          {message.historyId && !message.feedback && (
            <div className="flex gap-1">
              <button
                onClick={() => handleFeedback('like')}
                className="p-1 rounded-full hover:bg-green-500/10 text-slate-400 hover:text-green-500 transition-colors text-xs"
                title="ถูกใจ"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedback('dislike')}
                className="p-1 rounded-full hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors text-xs"
                title="ไม่ถูกใจ"
              >
                👎
              </button>
            </div>
          )}

          {message.feedback && (
            <span className="text-xs text-slate-400">
              {message.feedback === 'like' ? '👍 ขอบคุณสำหรับ Feedback ครับ' : '👎 รับทราบแล้วครับ'}
            </span>
          )}
        </div>

        {/* Feedback Comment Box */}
        {showFeedbackInput && (
          <div className="mt-2 glass-panel p-3 rounded-xl">
            <p className="text-xs text-slate-500 mb-1.5">บอกเราได้ว่าไม่พอใจตรงไหน?</p>
            <textarea
              value={feedbackComment}
              onChange={e => setFeedbackComment(e.target.value)}
              className="w-full text-sm p-2 rounded-lg glass-input resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              rows={2}
              placeholder="ความคิดเห็นเพิ่มเติม (ไม่บังคับ)"
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={submitFeedback}
                className="text-xs px-3 py-1.5 bg-tuh-gradient-1 text-white rounded-lg hover:opacity-90 transition-opacity"
              >
                ส่ง Feedback
              </button>
              <button
                onClick={() => setShowFeedbackInput(false)}
                className="text-xs px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg hover:opacity-80 transition-opacity"
              >
                ยกเลิก
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
