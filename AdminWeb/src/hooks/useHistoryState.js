import { useState, useEffect } from 'react';

/**
 * useHistoryState — ประวัติการตอบของบอท (ChatHistory), การกรองตามช่วงเวลา/วันที่, ส่งออก CSV,
 * แผนที่ chunk→เอกสารต้นทาง (chunksMap) และสถิติความพึงพอใจแยกตามช่วงเวลาสำหรับหน้าสถิติ
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 *
 * รับ feedback array มาจาก useFeedbackAndUnansweredState เพราะ getSatisfactionStatsByPeriod
 * เดิมอยู่ใกล้กับ state ของ History ในไฟล์เดิม (จัดกลุ่มตามตำแหน่งเดิมในซอร์สโค้ด) แต่คำนวณจาก
 * ข้อมูล feedback ของอีกโดเมนหนึ่ง
 */
export function useHistoryState(API_URL, fetch, feedback) {
  const [history, setHistory] = useState([]);
  const [chunksMap, setChunksMap] = useState({});
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [satPeriod, setSatPeriod] = useState('weekly');
  const [historyPeriod, setHistoryPeriod] = useState('weekly');

  // Sort and Date Filter States for History
  const [historySortOrder, setHistorySortOrder] = useState('desc'); // 'desc' = newest first, 'asc' = oldest first
  const [historyStartDate, setHistoryStartDate] = useState('');
  const [historyEndDate, setHistoryEndDate] = useState('');
  const [historyLimit, setHistoryLimit] = useState(() => {
    return localStorage.getItem('tuh_admin_history_limit') || '1000';
  });

  // Persist History Limit Preference
  useEffect(() => {
    localStorage.setItem('tuh_admin_history_limit', historyLimit);
  }, [historyLimit]);

  const parseTimestamp = (tsStr) => {
    if (!tsStr) return new Date(0);
    const parts = tsStr.split(" ");
    if (parts.length < 2) return new Date(tsStr);
    const [datePart, timePart] = parts;
    const [year, month, day] = datePart.split("-").map(Number);
    const [hour, minute, second] = timePart.split(":").map(Number);
    return new Date(year, month - 1, day, hour, minute, second);
  };

  const fetchHistoryChunksMap = () => {
    fetch(API_URL + '/api/admin/history/chunks-map')
      .then(r => r.json())
      .then(data => {
        setChunksMap(data || {});
      })
      .catch(err => console.error("Error fetching chunks map:", err));
  };

  const fetchHistory = () => {
    setLoadingHistory(true);
    // backend ตั้ง limit เริ่มต้นไว้ 100 — ขอเพิ่มให้ยอดตรงกับการ์ดหน้าภาพรวม (นับทั้งตาราง)
    fetch(API_URL + '/api/admin/history?limit=5000')
      .then(r => r.json())
      .then(data => {
        const sortedData = (data || []).reverse();
        setHistory(sortedData);
      })
      .catch(err => console.error("Error fetching history:", err))
      .finally(() => setLoadingHistory(false));
  };

  const filteredHistory = history.filter(log => {
    const logDate = parseTimestamp(log.timestamp);
    if (!logDate) return false;

    // If custom range is set, filter by it instead of the predefined period
    if (historyStartDate || historyEndDate) {
      if (historyStartDate) {
        const start = new Date(historyStartDate);
        start.setHours(0, 0, 0, 0);
        if (logDate < start) return false;
      }
      if (historyEndDate) {
        const end = new Date(historyEndDate);
        end.setHours(23, 59, 59, 999);
        if (logDate > end) return false;
      }
      return true;
    }

    if (historyPeriod === 'all') return true;
    const now = new Date();

    if (historyPeriod === 'daily') {
      return logDate.toDateString() === now.toDateString();
    }
    if (historyPeriod === 'weekly') {
      const day = now.getDay();
      const diffToMonday = day === 0 ? 6 : day - 1;
      const monday = new Date(now);
      monday.setDate(now.getDate() - diffToMonday);
      monday.setHours(0, 0, 0, 0);
      return logDate >= monday;
    }
    if (historyPeriod === 'monthly') {
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
      return logDate >= startOfMonth;
    }
    if (historyPeriod === 'yearly') {
      const startOfYear = new Date(now.getFullYear(), 0, 1, 0, 0, 0, 0);
      return logDate >= startOfYear;
    }
    return true;
  });

  const downloadCSV = () => {
    const sorted = [...filteredHistory].sort((a, b) => {
      const dateA = parseTimestamp(a.timestamp);
      const dateB = parseTimestamp(b.timestamp);
      return historySortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });
    const limitVal = historyLimit === 'all' ? sorted.length : parseInt(historyLimit, 10);
    const sliced = sorted.slice(0, limitVal);
    if (sliced.length === 0) return;
    const headers = ["เวลาที่ตอบ", "คำถามจากผู้ใช้", "คำตอบที่บอทตอบออกไป", "โมเดล AI", "Chunk ID", "เวลาตอบสนอง (วินาที)"];
    const rows = sliced.map(log => [
      log.timestamp,
      log.query,
      log.answer,
      log.api_model || log.model || "Direct FAQ",
      (log.chunk_ids || []).join(", "),
      log.response_time
    ]);
    const csvContent = [
      "﻿" + headers.map(h => `"${h.replace(/"/g, '""')}"`).join(","),
      ...rows.map(row => row.map(val => `"${String(val || '').replace(/"/g, '""')}"`).join(","))
    ].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);

    let periodText = 'all';
    if (historyPeriod === 'daily') periodText = 'daily';
    else if (historyPeriod === 'weekly') periodText = 'weekly';
    else if (historyPeriod === 'monthly') periodText = 'monthly';
    else if (historyPeriod === 'yearly') periodText = 'yearly';

    link.setAttribute("download", `bot_history_${periodText}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getSatisfactionStatsByPeriod = (period) => {
    const now = new Date();
    let filtered = [];
    let groupings = {};

    if (period === 'daily') {
      filtered = feedback.filter(fb => {
        const d = parseTimestamp(fb.timestamp);
        return d.toDateString() === now.toDateString();
      });
      for (let i = 0; i < 24; i += 2) {
        const label = `${String(i).padStart(2, '0')}:00 - ${String(i + 2).padStart(2, '0')}:00`;
        groupings[label] = { likes: 0, dislikes: 0 };
      }
      filtered.forEach(fb => {
        if (fb.answer && fb.answer.trim() !== "") {
          const d = parseTimestamp(fb.timestamp);
          const hour = d.getHours();
          const block = Math.floor(hour / 2) * 2;
          const label = `${String(block).padStart(2, '0')}:00 - ${String(block + 2).padStart(2, '0')}:00`;
          if (groupings[label]) {
            if (fb.rating === 'like') groupings[label].likes++;
            else groupings[label].dislikes++;
          }
        }
      });
    } else if (period === 'weekly') {
      filtered = feedback.filter(fb => {
        const d = parseTimestamp(fb.timestamp);
        return (now - d) <= (7 * 24 * 60 * 60 * 1000);
      });
      const thaiDays = ["อาทิตย์", "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์"];
      for (let i = 6; i >= 0; i--) {
        const tempDate = new Date();
        tempDate.setDate(now.getDate() - i);
        const dayLabel = thaiDays[tempDate.getDay()];
        const dateStr = `${tempDate.getDate()}/${tempDate.getMonth() + 1}`;
        const label = `${dayLabel} (${dateStr})`;
        groupings[label] = { likes: 0, dislikes: 0, keyDateStr: tempDate.toDateString() };
      }
      filtered.forEach(fb => {
        if (fb.answer && fb.answer.trim() !== "") {
          const fbDate = parseTimestamp(fb.timestamp);
          const fbDateStr = fbDate.toDateString();
          for (const [label, data] of Object.entries(groupings)) {
            if (data.keyDateStr === fbDateStr) {
              if (fb.rating === 'like') data.likes++;
              else data.dislikes++;
            }
          }
        }
      });
    } else if (period === 'monthly') {
      filtered = feedback.filter(fb => {
        const d = parseTimestamp(fb.timestamp);
        return (now - d) <= (30 * 24 * 60 * 60 * 1000);
      });
      for (let i = 4; i >= 1; i--) {
        groupings[`สัปดาห์ที่ ${i}`] = { likes: 0, dislikes: 0 };
      }
      filtered.forEach(fb => {
        if (fb.answer && fb.answer.trim() !== "") {
          const fbDate = parseTimestamp(fb.timestamp);
          const diffDays = Math.floor((now - fbDate) / (24 * 60 * 60 * 1000));
          let weekIndex = 4 - Math.floor(diffDays / 7);
          if (weekIndex < 1) weekIndex = 1;
          if (weekIndex > 4) weekIndex = 4;
          const label = `สัปดาห์ที่ ${weekIndex}`;
          if (groupings[label]) {
            if (fb.rating === 'like') groupings[label].likes++;
            else groupings[label].dislikes++;
          }
        }
      });
    } else if (period === 'yearly') {
      filtered = feedback.filter(fb => {
        const d = parseTimestamp(fb.timestamp);
        return (now - d) <= (365 * 24 * 60 * 60 * 1000);
      });
      const thaiMonths = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
      for (let i = 11; i >= 0; i--) {
        const tempDate = new Date();
        tempDate.setMonth(now.getMonth() - i);
        const label = thaiMonths[tempDate.getMonth()];
        groupings[label] = { likes: 0, dislikes: 0, yearMonthKey: `${tempDate.getFullYear()}-${tempDate.getMonth()}` };
      }
      filtered.forEach(fb => {
        if (fb.answer && fb.answer.trim() !== "") {
          const fbDate = parseTimestamp(fb.timestamp);
          const ymKey = `${fbDate.getFullYear()}-${fbDate.getMonth()}`;
          for (const [label, data] of Object.entries(groupings)) {
            if (data.yearMonthKey === ymKey) {
              if (fb.rating === 'like') data.likes++;
              else data.dislikes++;
            }
          }
        }
      });
    }

    let totalLikes = 0;
    let totalDislikes = 0;
    let starCounts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    let totalStarsCount = 0;

    filtered.forEach(fb => {
      if (fb.answer && fb.answer.trim() !== "") {
        if (fb.rating === 'like') totalLikes++;
        else totalDislikes++;
      } else if (fb.stars !== undefined && fb.stars !== null) {
        // นับเฉพาะรายการที่มีคะแนนดาวจริงจากผู้ใช้ ไม่เดาคะแนนจาก like/dislike เพื่อไม่ให้ค่าเฉลี่ยเพี้ยน
        const starsVal = parseInt(fb.stars);
        if (starCounts[starsVal] !== undefined) {
          starCounts[starsVal]++;
          totalStarsCount++;
        }
      }
    });

    const satRate = totalLikes + totalDislikes > 0 ? Math.round((totalLikes / (totalLikes + totalDislikes)) * 100) : 100;

    const list = Object.entries(groupings).map(([label, data]) => {
      const total = data.likes + data.dislikes;
      const rate = total > 0 ? Math.round((data.likes / total) * 100) : 100;
      return {
        label,
        likes: data.likes,
        dislikes: data.dislikes,
        total,
        rate
      };
    });

    const comments = filtered.filter(fb => fb.comment.trim() !== "");
    const starComments = filtered.filter(fb => fb.comment.trim() !== "" && (!fb.answer || fb.answer.trim() === ""));
    const dislikeComments = filtered.filter(fb => fb.comment.trim() !== "" && (fb.answer && fb.answer.trim() !== ""));

    return {
      filtered,
      totalLikes,
      totalDislikes,
      totalVotes: totalLikes + totalDislikes,
      satRate,
      chartData: list,
      comments,
      starCounts,
      totalStarsCount,
      starComments,
      dislikeComments
    };
  };

  return {
    history,
    setHistory,
    chunksMap,
    setChunksMap,
    loadingHistory,
    satPeriod,
    setSatPeriod,
    historyPeriod,
    setHistoryPeriod,
    historySortOrder,
    setHistorySortOrder,
    historyStartDate,
    setHistoryStartDate,
    historyEndDate,
    setHistoryEndDate,
    historyLimit,
    setHistoryLimit,
    parseTimestamp,
    fetchHistoryChunksMap,
    fetchHistory,
    filteredHistory,
    downloadCSV,
    getSatisfactionStatsByPeriod,
  };
}
