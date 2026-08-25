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
  parseMarkdown
}) => {
  const isBot = msg.sender === 'bot';

  return (
    <div
      className={`flex gap-2 max-w-[60%] ${isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'} animate-slide-in`}
    >
      {/* ไอคอนอวาตาร์ */}
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

      {/* ฟองคำพูด */}
      <div className="space-y-1 min-w-0">
        <div className={`text-base leading-relaxed break-words ${isBot
          ? 'p-3 rounded-2xl shadow-sm bg-slate-100 dark:bg-[#07010f] border border-slate-200/60 dark:border-tuh-purple/20 text-tuh-navy dark:text-white rounded-tl-sm'
          : 'p-3 rounded-2xl shadow-md bg-[#f8bbd0] text-black dark:bg-[#ad1457] dark:text-white rounded-tr-sm'
          }`}>
          {parseMarkdown(msg.text)}
        </div>

        {isBot ? (
          <div className="flex items-center gap-1.5 mt-1 px-0.5">
            <button
              onClick={() => handleLikeMessage(msg.id, 'like')}
              className={`p-1 rounded-md text-[13px] transition-all ${msg.liked ? 'text-emerald-500 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-500 dark:hover:text-emerald-400'}`}
            >
              <i className={`fa-thumbs-up ${msg.liked ? 'fa-solid' : 'fa-regular'}`}></i>
            </button>
            <button
              onClick={() => handleLikeMessage(msg.id, 'dislike')}
              className={`p-1 rounded-md text-[13px] transition-all ${msg.disliked ? 'text-red-500 bg-red-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-red-500 dark:hover:text-red-400'}`}
            >
              <i className={`fa-thumbs-down ${msg.disliked ? 'fa-solid' : 'fa-regular'}`}></i>
            </button>
            <button
              onClick={() => handleCopyMessage(msg.text, msg.id)}
              className={`p-1 rounded-md text-[13px] transition-all flex items-center gap-0.5 ${copiedId === msg.id ? 'text-emerald-600 bg-emerald-500/10' : 'text-tuh-indigo/35 dark:text-slate-400/50 hover:text-emerald-600 dark:hover:text-emerald-400'}`}
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
            <button
              onClick={() => {
                setInputValue(msg.text);
                const textarea = document.querySelector('.floating-textarea');
                if (textarea) textarea.focus();
              }}
              disabled={isTyping}
              className="p-0.5 rounded-md text-[13px] text-tuh-indigo/35 dark:text-slate-400/50 hover:text-orange-500 dark:hover:text-orange-400"
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
