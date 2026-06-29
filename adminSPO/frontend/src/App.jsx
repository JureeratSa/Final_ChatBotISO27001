import React, { useState, useEffect } from 'react';
import dog from './dog.png';

const API_URL = `http://${window.location.hostname}:8000`;

function App() {
  // Theme state
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('tuh_admin_theme');
    return saved === 'dark';
  });

  // Authentication State
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return localStorage.getItem('tuh_admin_token') !== null;
  });
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // Profile data
  const [adminUser, setAdminUser] = useState(() => {
    const saved = localStorage.getItem('tuh_admin_user');
    return saved ? JSON.parse(saved) : { name: 'แอดมิน สารสนเทศ', role: 'System Administrator', email: 'it@tuh.ac.th' };
  });
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Dashboard Tabs
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Application Data States
  const [stats, setStats] = useState({
    total_documents: 0,
    active_documents: 0,
    total_queries: 0,
    likes: 0,
    dislikes: 0,
    pending_unanswered: 0,
    recent_comments: []
  });
  const [documents, setDocuments] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [settings, setSettings] = useState({
    gemini_api_key: '',
    model_name: 'gemini-2.5-flash',
    temperature: 0.2,
    max_tokens: 400,
    top_k: 3,
    system_prompt: '',
    welcome_message: '',
    custom_faqs: [],
    predefined_faqs: [],
    embedding_tech: 'local_faiss'
  });

  // UI States
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [showFaqModal, setShowFaqModal] = useState(false);
  const [currentUnanswered, setCurrentUnanswered] = useState(null);
  const [faqAnswer, setFaqAnswer] = useState('');

  // Predefined FAQs Edit States
  const [showEditPredefinedFaqModal, setShowEditPredefinedFaqModal] = useState(false);
  const [selectedPredefinedFaq, setSelectedPredefinedFaq] = useState(null);
  const [predefinedFaqQuestion, setPredefinedFaqQuestion] = useState('');
  const [predefinedFaqAnswer, setPredefinedFaqAnswer] = useState('');
  const [predefinedFaqIcon, setPredefinedFaqIcon] = useState('');

  // Page Exclusions Edit State
  const [showEditDocModal, setShowEditDocModal] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [excludePagesInput, setExcludePagesInput] = useState('');

  // Bot Response History States
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [satPeriod, setSatPeriod] = useState('weekly');
  const [historyPeriod, setHistoryPeriod] = useState('weekly');

  // Password Visibility Toggle States
  const [showPassword, setShowPassword] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Sync Theme with HTML Class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tuh_admin_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tuh_admin_theme', 'light');
    }
  }, [isDarkMode]);

  // Fetch data on login
  useEffect(() => {
    if (isLoggedIn) {
      fetchStats();
      fetchDocuments();
      fetchFeedback();
      fetchUnanswered();
      fetchSettings();
      fetchHistory();
    }
  }, [isLoggedIn]);

  // Refetch history when switching to history tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, isLoggedIn]);

  // Alert Banner Helpers
  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };
  const showError = (msg) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(''), 4000);
  };

  // API Call Helpers
  const fetchStats = () => {
    fetch(API_URL + '/api/admin/stats')
      .then(r => r.json())
      .then(data => setStats(data))
      .catch(err => console.error("Error fetching stats:", err));
  };

  const fetchDocuments = () => {
    fetch(API_URL + '/api/admin/documents')
      .then(r => r.json())
      .then(data => setDocuments(data))
      .catch(err => console.error("Error fetching documents:", err));
  };

  const fetchFeedback = () => {
    fetch(API_URL + '/api/admin/feedback')
      .then(r => r.json())
      .then(data => setFeedback(data))
      .catch(err => console.error("Error fetching feedback:", err));
  };

  const fetchUnanswered = () => {
    fetch(API_URL + '/api/admin/unanswered')
      .then(r => r.json())
      .then(data => setUnanswered(data))
      .catch(err => console.error("Error fetching unanswered:", err));
  };

  const fetchSettings = () => {
    fetch(API_URL + '/api/admin/settings')
      .then(r => r.json())
      .then(data => {
        // Initialize default empty array for custom_faqs and predefined_faqs if not present
        if (!data.custom_faqs) data.custom_faqs = [];
        if (!data.predefined_faqs) data.predefined_faqs = [];
        setSettings(data);
      })
      .catch(err => console.error("Error fetching settings:", err));
  };

  const parseTimestamp = (tsStr) => {
    if (!tsStr) return new Date(0);
    const parts = tsStr.split(" ");
    if (parts.length < 2) return new Date(tsStr);
    const [datePart, timePart] = parts;
    const [year, month, day] = datePart.split("-").map(Number);
    const [hour, minute, second] = timePart.split(":").map(Number);
    return new Date(year, month - 1, day, hour, minute, second);
  };

  const downloadCSV = () => {
    if (history.length === 0) return;
    const headers = ["เวลาที่ตอบ", "คำถามจากผู้ใช้", "คำตอบที่บอทตอบออกไป", "โมเดล AI", "Chunk ID", "เวลาตอบสนอง (วินาที)"];
    const rows = history.map(log => [
      log.timestamp,
      log.query,
      log.answer,
      log.model,
      (log.chunk_ids || []).join(", "),
      log.response_time
    ]);
    const csvContent = [
      "\ufeff" + headers.map(h => `"${h.replace(/"/g, '""')}"`).join(","),
      ...rows.map(row => row.map(val => `"${String(val || '').replace(/"/g, '""')}"`).join(","))
    ].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `bot_history_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const fetchHistory = () => {
    setLoadingHistory(true);
    fetch(API_URL + '/api/admin/history')
      .then(r => r.json())
      .then(data => {
        const sortedData = (data || []).reverse();
        setHistory(sortedData);
      })
      .catch(err => console.error("Error fetching history:", err))
      .finally(() => setLoadingHistory(false));
  };

  const filteredHistory = history.filter(log => {
    if (historyPeriod === 'all') return true;
    const logDate = parseTimestamp(log.timestamp);
    const now = new Date();
    const diffTime = now - logDate;
    const diffDays = diffTime / (1000 * 60 * 60 * 24);
    if (historyPeriod === 'daily') return logDate.toDateString() === now.toDateString();
    if (historyPeriod === 'weekly') return diffDays <= 7;
    if (historyPeriod === 'monthly') return diffDays <= 30;
    if (historyPeriod === 'yearly') return diffDays <= 365;
    return true;
  });

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
        const d = parseTimestamp(fb.timestamp);
        const hour = d.getHours();
        const block = Math.floor(hour / 2) * 2;
        const label = `${String(block).padStart(2, '0')}:00 - ${String(block + 2).padStart(2, '0')}:00`;
        if (groupings[label]) {
          if (fb.rating === 'like') groupings[label].likes++;
          else groupings[label].dislikes++;
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
        const fbDate = parseTimestamp(fb.timestamp);
        const fbDateStr = fbDate.toDateString();
        for (const [label, data] of Object.entries(groupings)) {
          if (data.keyDateStr === fbDateStr) {
            if (fb.rating === 'like') data.likes++;
            else data.dislikes++;
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
        const fbDate = parseTimestamp(fb.timestamp);
        const ymKey = `${fbDate.getFullYear()}-${fbDate.getMonth()}`;
        for (const [label, data] of Object.entries(groupings)) {
          if (data.yearMonthKey === ymKey) {
            if (fb.rating === 'like') data.likes++;
            else data.dislikes++;
          }
        }
      });
    }

    let totalLikes = 0;
    let totalDislikes = 0;
    filtered.forEach(fb => {
      if (fb.rating === 'like') totalLikes++;
      else totalDislikes++;
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

    return {
      filtered,
      totalLikes,
      totalDislikes,
      totalVotes: totalLikes + totalDislikes,
      satRate,
      chartData: list,
      comments
    };
  };

  const getCategoryStats = (filteredFeedback) => {
    const categories = {
      "สวัสดิการและสิทธิ์การรักษา": { likes: 0, dislikes: 0 },
      "เวลาทำการและคลินิก": { likes: 0, dislikes: 0 },
      "การติดต่อหน่วยงาน": { likes: 0, dislikes: 0 },
      "เวชระเบียนและบัตรผู้ป่วย": { likes: 0, dislikes: 0 },
      "สอบถามข้อมูลทั่วไป": { likes: 0, dislikes: 0 }
    };

    filteredFeedback.forEach(fb => {
      const q = (fb.query || "").toLowerCase();
      let category = "สอบถามข้อมูลทั่วไป";
      if (q.includes("เบิก") || q.includes("เงิน") || q.includes("สิทธิ์") || q.includes("สวัสดิการ")) {
        category = "สวัสดิการและสิทธิ์การรักษา";
      } else if (q.includes("คลินิก") || q.includes("เวลา") || q.includes("เปิด") || q.includes("ทำการ")) {
        category = "เวลาทำการและคลินิก";
      } else if (q.includes("ติดต่อ") || q.includes("เบอร์") || q.includes("โทร")) {
        category = "การติดต่อหน่วยงาน";
      } else if (q.includes("บัตร") || q.includes("ใหม่") || q.includes("ทะเบียน") || q.includes("เปิดสิทธิ์")) {
        category = "เวชระเบียนและบัตรผู้ป่วย";
      }

      if (fb.rating === 'like') categories[category].likes++;
      else categories[category].dislikes++;
    });

    return Object.entries(categories).map(([name, data]) => {
      const total = data.likes + data.dislikes;
      const rate = total > 0 ? Math.round((data.likes / total) * 100) : 100;
      return { name, likes: data.likes, dislikes: data.dislikes, total, rate };
    }).filter(cat => cat.total > 0);
  };

  // Actions
  const handleLogin = (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    fetch(API_URL + '/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
      .then(res => {
        if (!res.ok) throw new Error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง");
        return res.json();
      })
      .then(data => {
        localStorage.setItem('tuh_admin_token', data.token);
        localStorage.setItem('tuh_admin_user', JSON.stringify(data));
        setAdminUser(data);
        setIsLoggedIn(true);
        showSuccess("เข้าสู่ระบบเรียบร้อยแล้ว");
      })
      .catch(err => {
        setLoginError(err.message);
      })
      .finally(() => {
        setLoginLoading(false);
      });
  };

  const handleLogout = () => {
    localStorage.removeItem('tuh_admin_token');
    localStorage.removeItem('tuh_admin_user');
    setIsLoggedIn(false);
  };

  const handleUpdatePassword = (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showError("รหัสผ่านไม่ตรงกัน");
      return;
    }
    if (newPassword.length < 4) {
      showError("รหัสผ่านสั้นเกินไป");
      return;
    }
    // Simulate password update
    showSuccess("เปลี่ยนรหัสผ่านแอดมินสำเร็จแล้ว (สำหรับใช้ครั้งถัดไป)");
    setNewPassword('');
    setConfirmPassword('');
  };

  const handleToggleDocStatus = (filename, currentStatus) => {
    const newActive = currentStatus !== 'Active';
    fetch(API_URL + '/api/admin/documents/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, active: newActive })
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess(`เปลี่ยนสถานะเอกสารสำเร็จ: ${newActive ? 'เปิดใช้งาน' : 'ปิดใช้งาน'}`);
          fetchDocuments();
          fetchStats();
        } else {
          showError("เกิดข้อผิดพลาดในการเปลี่ยนสถานะ");
        }
      })
      .catch(err => showError("เชื่อมต่อเซิร์ฟเวอร์ผิดพลาด"));
  };

  const handleDeleteDoc = (filename) => {
    if (!confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบเอกสาร "${filename}"? ข้อมูลใน Vector Index ของเอกสารนี้จะถูกนำออกทั้งหมด`)) return;

    fetch(API_URL + '/api/admin/documents/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลบเอกสารและเริ่มปรับปรุงฐานข้อมูลดัชนีเรียบร้อยแล้ว");
          fetchDocuments();
          fetchStats();
        } else {
          showError("เกิดข้อผิดพลาดในการลบเอกสาร");
        }
      })
      .catch(err => showError("ลบเอกสารไม่สำเร็จ"));
  };

  const handleOpenEditDocModal = (doc) => {
    setSelectedDoc(doc);
    setExcludePagesInput(doc.exclude_pages ? doc.exclude_pages.join(', ') : '');
    setShowEditDocModal(true);
  };

  const handleSaveExcludePages = (e) => {
    e.preventDefault();
    if (!selectedDoc) return;

    const pagesArray = excludePagesInput
      .split(',')
      .map(p => p.trim())
      .filter(p => p !== '' && !isNaN(p))
      .map(p => parseInt(p, 10));

    fetch(API_URL + '/api/admin/documents/update_exclude', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: selectedDoc.filename,
        exclude_pages: pagesArray
      })
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("ตั้งค่าหน้าเอกสารและกำลังสร้างสารบัญเวกเตอร์ใหม่...");
          fetchDocuments();
          fetchStats();
          setShowEditDocModal(false);
          setSelectedDoc(null);
        } else {
          showError("เกิดข้อผิดพลาดในการบันทึกข้อมูล");
        }
      })
      .catch(err => showError("เชื่อมต่อเซิร์ฟเวอร์ผิดพลาด"));
  };

  const handleSaveSettings = (e) => {
    e.preventDefault();
    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("บันทึกการตั้งค่าระบบ AI แชทบอทสำเร็จแล้ว");
          fetchSettings();
        } else {
          showError("บันทึกการตั้งค่าล้มเหลว");
        }
      })
      .catch(err => showError("ไม่สามารถเชื่อมต่อระบบหลังบ้านได้"));
  };

  const handleResolveUnanswered = (id, newStatus = "Resolved") => {
    fetch(API_URL + '/api/admin/unanswered/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, status: newStatus })
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("อัปเดตสถานะล็อกคำถามเรียบร้อยแล้ว");
          fetchUnanswered();
          fetchStats();
        }
      })
      .catch(err => console.error(err));
  };

  // Register answer to FAQ database
  const handleOpenFaqModal = (log) => {
    setCurrentUnanswered(log);
    setFaqAnswer('');
    setShowFaqModal(true);
  };

  const handleSubmitFaq = (e) => {
    e.preventDefault();
    if (!faqAnswer.trim()) return;

    const newFaq = {
      id: `faq-${Date.now()}`,
      question: currentUnanswered.query,
      answer: faqAnswer,
      timestamp: new Date().toLocaleDateString('th-TH')
    };

    // Update settings custom FAQs
    const updatedFaqs = [...(settings.custom_faqs || []), newFaq];
    const updatedSettings = { ...settings, custom_faqs: updatedFaqs };

    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลงทะเบียนคู่มือคำตอบ (FAQ) สำเร็จ บอทจะตอบด้วยคำตอบนี้ในแชททันที");
          setSettings(updatedSettings);
          // Auto resolve the unanswered status
          handleResolveUnanswered(currentUnanswered.id, "Resolved");
          setShowFaqModal(false);
          setCurrentUnanswered(null);
        } else {
          showError("เกิดข้อผิดพลาดในการลงทะเบียนคำตอบ");
        }
      })
      .catch(err => showError("เชื่อมต่อล้มเหลว"));
  };

  const handleDeleteFaq = (faqId) => {
    if (!confirm("คุณต้องการลบคู่มือคำตอบ FAQ รายการนี้ใช่หรือไม่?")) return;

    const updatedFaqs = settings.custom_faqs.filter(f => f.id !== faqId);
    const updatedSettings = { ...settings, custom_faqs: updatedFaqs };

    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลบรายการ FAQ เรียบร้อยแล้ว");
          setSettings(updatedSettings);
        }
      })
      .catch(err => showError("ลบไม่สำเร็จ"));
  };

  const handleOpenEditPredefinedFaqModal = (faq) => {
    setSelectedPredefinedFaq(faq);
    setPredefinedFaqQuestion(faq.question);
    setPredefinedFaqAnswer(faq.answer || faq.response || '');
    setPredefinedFaqIcon(faq.icon || 'fa-circle-question');
    setShowEditPredefinedFaqModal(true);
  };

  const handleSavePredefinedFaq = (e) => {
    e.preventDefault();
    if (!selectedPredefinedFaq) return;

    const updatedPredefinedFaqs = settings.predefined_faqs.map(faq => {
      if (faq.id === selectedPredefinedFaq.id) {
        return {
          ...faq,
          question: predefinedFaqQuestion,
          answer: '',
          response: '', // Keep answer empty to enforce RAG search on PDF
          icon: faq.icon || 'fa-circle-question'
        };
      }
      return faq;
    });

    const updatedSettings = {
      ...settings,
      predefined_faqs: updatedPredefinedFaqs
    };

    fetch(API_URL + '/api/admin/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSettings)
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          showSuccess("บันทึกคำถามที่พบบ่อย (ปุ่มหน้าแรก) สำเร็จแล้ว");
          setSettings(updatedSettings);
          setShowEditPredefinedFaqModal(false);
          setSelectedPredefinedFaq(null);
        } else {
          showError("บันทึกการเปลี่ยนแปลงล้มเหลว");
        }
      })
      .catch(err => showError("เชื่อมต่อเซิร์ฟเวอร์หลังบ้านล้มเหลว"));
  };

  // PDF File Upload Handler
  const uploadFile = (file) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showError("ระบบสนับสนุนการอัปโหลดไฟล์นามสกุล .pdf เท่านั้น");
      return;
    }

    setUploading(true);
    setUploadProgress(10);

    const reader = new FileReader();
    reader.readAsArrayBuffer(file);
    reader.onload = () => {
      setUploadProgress(40);
      const arrayBuffer = reader.result;

      fetch(API_URL + '/api/admin/documents/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/pdf',
          'X-File-Name': encodeURIComponent(file.name)
        },
        body: arrayBuffer
      })
        .then(res => {
          if (!res.ok) throw new Error("การอัปโหลดล้มเหลว");
          return res.json();
        })
        .then(data => {
          setUploadProgress(100);
          showSuccess("อัปโหลดสำเร็จแล้ว! ระบบกำลังสกัดคำและคำนวณเวกเตอร์ในเบื้องหลัง (ประมาณ 10-30 วินาที)");
          setTimeout(() => {
            setUploading(false);
            setUploadProgress(0);
          }, 1000);
          // Poll for update
          setTimeout(fetchDocuments, 2000);
          setTimeout(fetchDocuments, 8000);
        })
        .catch(err => {
          showError(`เกิดข้อผิดพลาดในการอัปโหลด: ${err.message}`);
          setUploading(false);
          setUploadProgress(0);
        });
    };
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  // Login View
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-tuh-navy text-white flex flex-col justify-center items-center relative overflow-hidden px-4">
        {/* Floating Light Elements */}
        <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/20 blur-[120px] pointer-events-none animate-float-slow"></div>
        <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full bg-tuh-rose/10 blur-[120px] pointer-events-none animate-float-slower"></div>

        <div className="w-full max-w-md bg-white/10 dark:bg-tuh-indigo/25 backdrop-blur-xl p-8 rounded-3xl border border-white/10 shadow-2xl relative z-10 animate-slide-in">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-tuh-gradient-2 mx-auto rounded-2xl flex items-center justify-center text-white text-3xl shadow-lg mb-4 animate-bounce">
              <i className="fa-solid fa-screwdriver-wrench"></i>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">TUH Chatbot Admin</h1>
            <p className="text-sm text-slate-300 mt-1">ระบบตั้งค่าและวิเคราะห์ข้อมูล สำหรับผู้ดูแลระบบ</p>
          </div>

          {loginError && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-2xl text-red-200 text-sm flex items-center gap-2 font-medium">
              <i className="fa-solid fa-circle-exclamation text-base"></i>
              {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">Username</label>
              <div className="relative">
                <i className="fa-solid fa-user absolute left-4 top-3.5 text-slate-400"></i>
                <input
                  type="text"
                  required
                  placeholder="ชื่อผู้ใช้งานแอดมิน"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-11 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">Password</label>
              <div className="relative">
                <i className="fa-solid fa-lock absolute left-4 top-3.5 text-slate-400"></i>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="รหัสผ่านเข้าใช้งาน"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 pl-11 pr-12 text-white placeholder-slate-500 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-400 transition-colors focus:outline-none cursor-pointer"
                >
                  <i className={`fa-solid ${showPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full bg-tuh-gradient-2 text-white font-bold py-3.5 rounded-2xl hover:shadow-lg hover:shadow-tuh-rose/30 hover:scale-[1.02] transition active:scale-[0.98] flex justify-center items-center gap-2"
            >
              {loginLoading ? (
                <>
                  <i className="fa-solid fa-circle-notch animate-spin"></i>
                  กำลังตรวจสอบสิทธิ์...
                </>
              ) : (
                <>
                  <i className="fa-solid fa-right-to-bracket"></i>
                  เข้าสู่ระบบแอดมิน
                </>
              )}
            </button>
          </form>

          <div className="mt-8 text-center text-xs text-slate-400 font-semibold">
            งานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Main View
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-tuh-navy dark:bg-[#100220] dark:text-white transition-colors duration-300 font-sans">

      {/* Dynamic Floating Background Elements */}
      <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/5 dark:bg-tuh-purple/10 blur-[100px] pointer-events-none animate-float-slow"></div>
      <div className="absolute bottom-40 left-10 w-96 h-96 rounded-full bg-tuh-coral/5 dark:bg-tuh-rose/5 blur-[120px] pointer-events-none animate-float-slower"></div>

      {/* Notifications */}
      {successMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-emerald-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-check text-lg"></i>
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="fixed top-5 right-5 z-50 p-4 bg-red-500 text-white rounded-2xl shadow-xl flex items-center gap-2.5 font-bold animate-slide-in">
          <i className="fa-solid fa-circle-exclamation text-lg"></i>
          {errorMsg}
        </div>
      )}

      {/* Mobile Drawer Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden transition-opacity duration-300"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar Panel */}
      <aside className={`fixed inset-y-0 left-0 z-30 w-72 flex flex-col border-r border-slate-200 dark:border-tuh-purple/20 bg-white dark:bg-tuh-indigo/90 backdrop-blur-md transition-transform duration-300 lg:static lg:translate-x-0 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Header */}
        <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex items-center gap-3">
          <img
            src={dog}
            alt="TUH Dog Logo"
            className="w-10 h-10 rounded-xl object-cover shadow-md shrink-0 border border-slate-100 dark:border-tuh-purple/20"
          />
          <div>
            <h2 className="font-extrabold text-base text-tuh-navy dark:text-white leading-tight">TUH Admin Chatbot</h2>
            <a
              href="https://intranet.hospital.tu.ac.th/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-tuh-indigo/60 dark:text-white hover:text-tuh-rose dark:hover:text-tuh-pink font-bold block mt-0.5 leading-none transition-colors cursor-pointer"
            >
              Thammasat University Hospital
            </a>
          </div>
        </div>

        {/* Menu Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto custom-scrollbar">
          <button
            onClick={() => { setActiveTab('dashboard'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'dashboard' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-chart-line text-sm"></i>
            <span>ภาพรวม</span>
          </button>

          <button
            onClick={() => { setActiveTab('satisfaction'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'satisfaction' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-face-smile text-sm"></i>
            <span>สถิติความพึงพอใจ</span>
          </button>

          <button
            onClick={() => { setActiveTab('documents'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'documents' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-file-pdf text-sm"></i>
            <span>จัดการเอกสาร PDF</span>
          </button>

          <button
            onClick={() => { setActiveTab('logs'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'logs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <div className="relative">
              <i className="fa-solid fa-circle-question text-sm"></i>
              {stats.pending_unanswered > 0 && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-tuh-rose rounded-full animate-pulse"></span>
              )}
            </div>
            <span>คำถามที่บอทตอบไม่ได้</span>
            {stats.pending_unanswered > 0 && (
              <span className="ml-auto bg-tuh-rose text-white text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                {stats.pending_unanswered}
              </span>
            )}
          </button>

          <button
            onClick={() => { setActiveTab('history'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'history' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-clock-rotate-left text-sm"></i>
            <span>ประวัติการตอบของบอท</span>
          </button>

          <button
            onClick={() => { setActiveTab('faqs'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'faqs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-book text-sm"></i>
            <span>คู่มือตอบกลับ (FAQs)</span>
          </button>


          <button
            onClick={() => { setActiveTab('profile'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'profile' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-user-gear text-sm"></i>
            <span>โปรไฟล์แอดมิน</span>
          </button>

          <button
            onClick={() => { setActiveTab('settings'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'settings' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-sliders text-sm"></i>
            <span>ตั้งค่าระบบ AI</span>
          </button>
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-100 dark:border-tuh-purple/20 space-y-2 bg-slate-50/50 dark:bg-tuh-navy/40">
          {/* Theme Toggle */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-100 dark:hover:bg-tuh-indigo/40 text-tuh-navy dark:text-slate-100 transition-all font-semibold"
          >
            <div className="flex items-center gap-2.5">
              <i className={`fa-solid ${isDarkMode ? 'fa-sun text-amber-500 animate-spin-slow' : 'fa-moon text-tuh-rose'} text-base`}></i>
              <span>สลับโหมดสี</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 dark:bg-white/10 font-bold">
              {isDarkMode ? 'โหมดสว่าง' : 'โหมดมืด'}
            </span>
          </button>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 p-3 rounded-xl hover:bg-red-50 dark:hover:bg-red-500/10 text-red-500 transition font-bold text-left"
          >
            <i className="fa-solid fa-arrow-right-from-bracket"></i>
            <span>ออกจากระบบ</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Navbar */}
        <header className="p-4 md:px-6 border-b border-slate-200 dark:border-tuh-purple/20 bg-white/70 dark:bg-tuh-navy/40 backdrop-blur-md flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-tuh-indigo/50 transition shrink-0"
            >
              <i className="fa-solid fa-bars text-lg"></i>
            </button>
            <h1 className="text-xl font-black tracking-tight flex items-center gap-2">
              <span className="text-tuh-rose shrink-0">
                {activeTab === 'dashboard' && <i className="fa-solid fa-chart-line"></i>}
                {activeTab === 'satisfaction' && <i className="fa-solid fa-face-smile"></i>}
                {activeTab === 'documents' && <i className="fa-solid fa-file-pdf"></i>}
                {activeTab === 'logs' && <i className="fa-solid fa-circle-question"></i>}
                {activeTab === 'history' && <i className="fa-solid fa-clock-rotate-left"></i>}
                {activeTab === 'faqs' && <i className="fa-solid fa-book"></i>}
                {activeTab === 'settings' && <i className="fa-solid fa-sliders"></i>}
                {activeTab === 'profile' && <i className="fa-solid fa-user-gear"></i>}
              </span>
              <span className={`${activeTab === 'dashboard' ? 'text-tuh-gradient-light' : 'text-tuh-gradient'} font-black`}>
                {activeTab === 'dashboard' && 'ภาพรวม'}
                {activeTab === 'satisfaction' && 'สถิติความพึงพอใจ'}
                {activeTab === 'documents' && 'จัดการแฟ้มเอกสาร PDF'}
                {activeTab === 'logs' && 'บันทึกคำถามที่บอทตอบไม่ได้'}
                {activeTab === 'history' && 'ประวัติการตอบของบอท'}
                {activeTab === 'faqs' && 'ทะเบียนคู่มือคำตอบ FAQs'}
                {activeTab === 'settings' && 'การตั้งค่าระบบ AI แชทบอท'}
                {activeTab === 'profile' && 'โปรไฟล์ผู้ดูแลระบบ'}
              </span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline text-xs font-bold px-3 py-1.5 rounded-full bg-tuh-pink/30 text-tuh-rose border border-tuh-rose/20 dark:bg-tuh-rose/25 dark:text-white dark:border-none shadow-sm">
              🧑‍💻 {adminUser.name} ({adminUser.role})
            </span>
          </div>
        </header>

        {/* Content Box */}
        <div className="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar z-10">

          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6 animate-slide-in">
              {/* Portal Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-slide-in">

                {/* 1. Q&A History Portal */}
                <div
                  onClick={() => setActiveTab('history')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-sky-500/40 dark:hover:border-sky-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>ประวัติการตอบของบอท</span>
                      <h3 className="text-3xl font-black tracking-tight text-sky-500">
                        {stats.total_queries} <span className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>คำถามทั้งหมด</span>
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-sky-500/10 text-sky-500 flex items-center justify-center text-base"><i className="fa-solid fa-clock-rotate-left"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      บันทึกคิวรีถามตอบของผู้ใช้ย้อนหลัง ความเร็วตอบสนอง และข้อมูลอ้างอิง
                    </p>
                    <span className="text-xs text-sky-500 font-bold flex items-center gap-1">เข้าสู่เมนูประวัติ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 2. Satisfaction Stats Portal */}
                <div
                  onClick={() => setActiveTab('satisfaction')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-emerald-500/40 dark:hover:border-emerald-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>สถิติความพึงพอใจ</span>
                      <h3 className="text-3xl font-black tracking-tight text-emerald-500">
                        {stats.likes + stats.dislikes > 0 ? Math.round((stats.likes / (stats.likes + stats.dislikes)) * 100) : 100}%
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-base"><i className="fa-solid fa-face-smile"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      วิเคราะห์ความพึงพอใจย้อนหลังรายวัน/สัปดาห์/เดือน/ปี และสถิติแยกตามหมวดหมู่คำถามหลัก
                    </p>
                    <span className="text-xs text-emerald-500 font-bold flex items-center gap-1">เข้าสู่เมนูสถิติ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 3. Unanswered Logs Portal */}
                <div
                  onClick={() => setActiveTab('logs')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-rose-500/40 dark:hover:border-rose-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>คำถามที่บอทตอบไม่ได้</span>
                      <h3 className={`text-3xl font-black tracking-tight ${stats.pending_unanswered > 0 ? (isDarkMode ? 'text-[#f06292]' : 'text-rose-500') : (isDarkMode ? 'text-white' : 'text-slate-500')}`}>
                        {stats.pending_unanswered} <span className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>คำถามค้างตอบ</span>
                      </h3>
                    </div>
                    <span className={`w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-base ${isDarkMode ? 'text-[#f06292]' : 'text-rose-500'}`}><i className="fa-solid fa-circle-question"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      คำถามจากผู้ใช้ที่บอทไม่มีความรู้อ้างอิง รอการเพิ่มคู่มือคำตอบจากแอดมินโดยตรง
                    </p>
                    <span className={`text-xs font-bold flex items-center gap-1 ${isDarkMode ? 'text-[#f06292]' : 'text-rose-500'}`}>เข้าสู่เมนูตอบคำถาม <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 4. PDF Manage Portal */}
                <div
                  onClick={() => setActiveTab('documents')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-purple-500/40 dark:hover:border-purple-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>จัดการเอกสาร PDF</span>
                      <h3 className={`text-3xl font-black tracking-tight ${isDarkMode ? 'text-[#f69988]' : 'text-purple-500'}`}>
                        {stats.active_documents} / {stats.total_documents} <span className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>แฟ้มเปิดใช้งาน</span>
                      </h3>
                    </div>
                    <span className={`w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-base ${isDarkMode ? 'text-[#f69988]' : 'text-purple-500'}`}><i className="fa-solid fa-file-pdf"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      อัปโหลดแฟ้มข้อมูล PDF ค้นหา ลบ และจัดการสิทธิ์การข้ามบางหน้าของการเรียนรู้ของระบบ RAG
                    </p>
                    <span className={`text-xs font-bold flex items-center gap-1 ${isDarkMode ? 'text-[#f69988]' : 'text-purple-500'}`}>เข้าสู่เมนูจัดการไฟล์ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 5. FAQs Portal */}
                <div
                  onClick={() => setActiveTab('faqs')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-amber-500/40 dark:hover:border-amber-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>คู่มือตอบกลับ (FAQs)</span>
                      <h3 className="text-3xl font-black tracking-tight text-amber-500">
                        6 <span className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>คำถามด่วนหน้าแรก</span>
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center text-base"><i className="fa-solid fa-book"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      จัดการไอคอน คำถาม และคำตอบด่วนสำหรับการคลิกถามยอดฮิต 6 ปุ่มบนหน้าแรกของผู้ใช้
                    </p>
                    <span className="text-xs text-amber-500 font-bold flex items-center gap-1">เข้าสู่เมนู FAQs <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 6. Admin Profile Portal */}
                <div
                  onClick={() => setActiveTab('profile')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-slate-500/40 dark:hover:border-slate-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between h-48"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>โปรไฟล์แอดมิน</span>
                      <h3 className={`text-3xl font-black tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-500'}`}>
                        ผู้ดูแล <span className={`text-xs font-bold ${isDarkMode ? 'text-white' : 'text-slate-450'}`}>ระบบไอที</span>
                      </h3>
                    </div>
                    <span className={`w-10 h-10 rounded-xl bg-slate-500/10 flex items-center justify-center text-base ${isDarkMode ? 'text-white' : 'text-slate-500'}`}><i className="fa-solid fa-user-gear"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[11px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-white' : 'text-slate-400'}`}>
                      ความปลอดภัย ข้อมูลประจำตัว บทบาท อีเมล และระบบเปลี่ยนรหัสผ่านในการเข้าใช้งานแผงจัดการ
                    </p>
                    <span className={`text-xs font-bold flex items-center gap-1 ${isDarkMode ? 'text-white' : 'text-slate-500'}`}>เข้าสู่เมนูโปรไฟล์ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: DOCUMENTS */}
          {activeTab === 'documents' && (
            <div className="space-y-6 animate-slide-in">
              {/* Drag n Drop upload file container */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`p-10 border-2 border-dashed rounded-3xl text-center transition ${dragOver
                    ? 'border-tuh-rose bg-tuh-pink/20 dark:bg-tuh-rose/10'
                    : 'border-slate-300 dark:border-tuh-purple/30 bg-white dark:bg-tuh-indigo/25'
                  }`}
              >
                {uploading ? (
                  <div className="space-y-4 max-w-md mx-auto">
                    <div className="w-12 h-12 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin mx-auto"></div>
                    <h3 className="text-lg font-bold">กำลังอัปโหลดเอกสาร PDF... ({uploadProgress}%)</h3>
                    <div className="w-full bg-slate-100 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                      <div className="bg-tuh-rose h-full rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="text-5xl text-tuh-rose/60"><i className="fa-solid fa-cloud-arrow-up"></i></div>
                    <div>
                      <h3 className="text-lg font-extrabold text-tuh-navy dark:text-white">ลากและวางไฟล์ PDF ของคุณที่นี่</h3>
                      <p className="text-sm text-slate-400 font-bold mt-1">ระบบรองรับไฟล์ระเบียบและเอกสารภาษาไทยนามสกุล PDF เท่านั้น</p>
                    </div>
                    <div>
                      <input
                        type="file"
                        id="pdf-uploader"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            uploadFile(e.target.files[0]);
                          }
                        }}
                      />
                      <label
                        htmlFor="pdf-uploader"
                        className="inline-flex items-center gap-2 bg-tuh-gradient-2 hover:shadow-lg text-white font-bold py-2.5 px-6 rounded-2xl cursor-pointer active:scale-[0.98] transition"
                      >
                        <i className="fa-solid fa-file-circle-plus"></i> เลือกไฟล์จากคอมพิวเตอร์
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Documents Table */}
              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-table text-tuh-rose"></i> แฟ้มเอกสารทั้งหมด</h3>
                  {stats.last_build_duration !== undefined && stats.last_build_duration !== null && (
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-black/20 px-3.5 py-1.5 rounded-full border border-slate-200/50 dark:border-tuh-purple/10">
                      ⏱️ สกัดเวกเตอร์ล่าสุดเสร็จสิ้นใน {stats.last_build_duration.toFixed(2)} วินาที
                    </span>
                  )}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-tuh-navy/30 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                        <th className="px-6 py-4">ชื่อไฟล์</th>
                        <th className="px-6 py-4">ขนาดไฟล์</th>
                        <th className="px-6 py-4 text-center">จำนวนหน้า</th>
                        <th className="px-6 py-4">วันที่อัปโหลด</th>
                        <th className="px-6 py-4 text-center">สถานะการทำงาน</th>
                        <th className="px-6 py-4 text-center">เปิดใช้งาน</th>
                        <th className="px-6 py-4 text-right">เครื่องมือ</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                      {documents.length === 0 ? (
                        <tr>
                          <td colSpan="7" className="px-6 py-8 text-center text-slate-400 font-bold">
                            ไม่มีไฟล์เอกสารที่บันทึกไว้ในขณะนี้
                          </td>
                        </tr>
                      ) : (
                        documents.map(doc => {
                          const isProcessing = doc.status === 'Processing';
                          const isActive = doc.status === 'Active';
                          return (
                            <tr key={doc.filename} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              <td className="px-6 py-4 font-bold max-w-[200px] truncate" title={doc.filename}>
                                <i className="fa-solid fa-file-pdf text-red-500 mr-2"></i>
                                {doc.filename}
                              </td>
                              <td className="px-6 py-4 text-xs font-bold text-slate-400">
                                {Math.round(doc.size / 1024)} KB
                              </td>
                              <td className="px-6 py-4 text-center">
                                <div>{doc.pages || '-'} หน้า</div>
                                {doc.exclude_pages && doc.exclude_pages.length > 0 && (
                                  <div className="text-[10px] text-red-500 font-bold bg-red-500/10 rounded-full px-2 py-0.5 inline-block mt-1">
                                    ละเว้นหน้า: {doc.exclude_pages.join(', ')}
                                  </div>
                                )}
                              </td>
                              <td className="px-6 py-4 text-xs text-slate-400">
                                {doc.upload_date}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isProcessing ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-500">
                                    <i className="fa-solid fa-circle-notch animate-spin"></i>
                                    กำลังสกัด/ปรับเวกเตอร์
                                  </span>
                                ) : doc.status === 'Error' ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-500">
                                    <i className="fa-solid fa-circle-xmark"></i>
                                    ผิดพลาด
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500">
                                    <i className="fa-solid fa-circle-check"></i>
                                    พร้อมใช้งาน
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {/* Status Toggle Switch */}
                                <button
                                  disabled={isProcessing}
                                  onClick={() => handleToggleDocStatus(doc.filename, doc.status)}
                                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${isActive ? 'bg-tuh-rose' : 'bg-slate-300 dark:bg-white/10'
                                    } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                  <span
                                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isActive ? 'translate-x-6' : 'translate-x-1'
                                      }`}
                                  />
                                </button>
                              </td>
                              <td className="px-6 py-4 text-right flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => handleOpenEditDocModal(doc)}
                                  className="p-2 text-tuh-rose hover:bg-tuh-rose/10 rounded-xl transition active:scale-95 flex items-center justify-center"
                                  title="ตั้งค่าละเว้นหน้าเอกสาร"
                                >
                                  <i className="fa-solid fa-gear text-sm"></i>
                                </button>
                                <button
                                  onClick={() => handleDeleteDoc(doc.filename)}
                                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-xl transition active:scale-95 flex items-center justify-center"
                                  title="ลบเอกสาร"
                                >
                                  <i className="fa-solid fa-trash-can text-sm"></i>
                                </button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {/* TAB 3: UNANSWERED LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-6 animate-slide-in">
              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20">
                  <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-triangle-exclamation text-tuh-rose"></i> รายชื่อคำถามที่บอทตอบไม่ได้</h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-tuh-navy/30 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                        <th className="px-6 py-4">ข้อความคำถาม</th>
                        <th className="px-6 py-4 text-center">ถามซ้ำ (จำนวน)</th>
                        <th className="px-6 py-4">ถามล่าสุดเมื่อ</th>
                        <th className="px-6 py-4 text-center">สถานะ</th>
                        <th className="px-6 py-4 text-right">เครื่องมือแก้ไข</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                      {unanswered.length === 0 ? (
                        <tr>
                          <td colSpan="5" className="px-6 py-8 text-center text-slate-400 font-bold">
                            ไม่มีคำถามที่ค้างการตอบในขณะนี้
                          </td>
                        </tr>
                      ) : (
                        [...unanswered].reverse().map(log => {
                          const isPending = log.status === 'Pending';
                          return (
                            <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              <td className="px-6 py-4 font-bold text-slate-800 dark:text-slate-100">
                                {log.query}
                              </td>
                              <td className="px-6 py-4 text-center font-black">
                                {log.count} ครั้ง
                              </td>
                              <td className="px-6 py-4 text-xs text-slate-400">
                                {log.timestamp}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isPending ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-tuh-rose">
                                    <i className="fa-solid fa-clock-rotate-left"></i>
                                    ค้างตอบ
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500">
                                    <i className="fa-solid fa-circle-check"></i>
                                    แก้ไขแล้ว
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4 text-right space-x-2">
                                {isPending && (
                                  <>
                                    <button
                                      onClick={() => handleOpenFaqModal(log)}
                                      className="inline-flex items-center gap-1 bg-emerald-500 text-white font-bold py-1.5 px-3 rounded-xl hover:bg-emerald-600 transition active:scale-95 text-xs"
                                    >
                                      <i className="fa-solid fa-feather"></i> ตอบคำถามนี้
                                    </button>
                                    <button
                                      onClick={() => handleResolveUnanswered(log.id, "Ignored")}
                                      className="inline-flex items-center gap-1 bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-slate-300 font-bold py-1.5 px-3 rounded-xl hover:bg-slate-300 transition active:scale-95 text-xs"
                                    >
                                      ละเว้น
                                    </button>
                                  </>
                                )}
                                {!isPending && (
                                  <button
                                    onClick={() => handleResolveUnanswered(log.id, "Pending")}
                                    className="text-xs text-tuh-rose hover:underline"
                                  >
                                    กู้คืนเป็นค้างตอบ
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB: HISTORY LOGS */}
          {activeTab === 'history' && (
            <div className="space-y-6 animate-slide-in">
              {/* TOP SUMMARY CARDS */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Metric Card: Questions Count */}
                <div className="p-6 bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex items-center justify-between col-span-1">
                  <div className="space-y-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-450 dark:text-slate-400">คำถามทั้งหมดที่โดนถาม</span>
                    <h3 className="text-3xl font-black tracking-tight text-sky-500">
                      {filteredHistory.length} <span className="text-xs font-bold text-slate-400">คำถาม</span>
                    </h3>
                    <p className="text-[10px] text-slate-400 font-semibold">
                      จากคำถามสะสมทั้งหมด {history.length} ในฐานข้อมูล
                    </p>
                  </div>
                  <span className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-500 flex items-center justify-center text-xl shrink-0"><i className="fa-solid fa-comments"></i></span>
                </div>

                {/* Period Switcher Card */}
                <div className="p-6 bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex flex-col justify-between col-span-2">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-450 dark:text-slate-400">ฟิลเตอร์สลับช่วงเวลาบันทึกประวัติ</span>
                    <p className="text-xs text-slate-450 dark:text-slate-400 font-semibold mt-1">เลือกช่วงเวลาเพื่อปรับการแสดงสถิติจำนวนคำถามและการแสดงตารางรายละเอียดด้านล่าง</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-4 lg:mt-0">
                    <div className="flex items-center bg-slate-100 dark:bg-tuh-navy/55 p-1 rounded-2xl border border-slate-200/50 dark:border-tuh-purple/10">
                      {[
                        { key: 'daily', label: 'รายวัน' },
                        { key: 'weekly', label: 'รายสัปดาห์' },
                        { key: 'monthly', label: 'รายเดือน' },
                        { key: 'yearly', label: 'รายปี' },
                        { key: 'all', label: 'ทั้งหมด' }
                      ].map(p => (
                        <button
                          key={p.key}
                          onClick={() => setHistoryPeriod(p.key)}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${historyPeriod === p.key ? 'bg-white dark:bg-tuh-purple/35 text-tuh-rose dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* TABLE CARD */}
              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-extrabold flex items-center gap-2">
                      <i className="fa-solid fa-clock-rotate-left text-tuh-rose"></i> ตารางรายการประวัติการตอบของบอท
                    </h3>
                    <p className="text-xs text-slate-450 dark:text-slate-400 font-semibold mt-1">
                      บันทึกรายการคำถาม-คำตอบ อ้างอิงตามระยะเวลาที่เลือก (ดาวน์โหลด CSV เพื่อส่งออกข้อมูลทั้งหมด)
                    </p>
                  </div>
                  <div className="flex items-center gap-2 self-start md:self-auto">
                    <button
                      onClick={downloadCSV}
                      disabled={history.length === 0}
                      className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs shadow-sm hover:shadow"
                    >
                      <i className="fa-solid fa-file-csv"></i> ดาวน์โหลด CSV
                    </button>
                    <button
                      onClick={fetchHistory}
                      className="bg-tuh-gradient-2 hover:shadow-lg text-white font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs"
                    >
                      <i className="fa-solid fa-arrows-rotate"></i> รีเฟรชประวัติ
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse min-w-[800px]">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-tuh-navy/30 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                        <th className="px-6 py-4 w-44">เวลาที่ตอบ</th>
                        <th className="px-6 py-4 w-64">คำถามจากผู้ใช้</th>
                        <th className="px-6 py-4">คำตอบที่บอทตอบออกไป</th>
                        <th className="px-6 py-4 w-44">โมเดล AI</th>
                        <th className="px-6 py-4 w-32 text-center">Chunk ID</th>
                        <th className="px-6 py-4 w-32 text-right">เวลาตอบสนอง</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                      {loadingHistory ? (
                        <tr>
                          <td colSpan="6" className="px-6 py-12 text-center text-slate-450 font-bold">
                            <div className="inline-block w-6 h-6 border-2 border-tuh-rose border-t-transparent rounded-full animate-spin mr-2"></div>
                            กำลังโหลดประวัติ...
                          </td>
                        </tr>
                      ) : filteredHistory.length === 0 ? (
                        <tr>
                          <td colSpan="6" className="px-6 py-12 text-center text-slate-400 font-bold">
                            ไม่มีประวัติการตอบคำถามในช่วงเวลาที่เลือก
                          </td>
                        </tr>
                      ) : (
                        filteredHistory.map((log) => {
                          const isFaq = log.model === "Direct FAQ";
                          return (
                            <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              {/* Time */}
                              <td className="px-6 py-4 text-xs text-slate-400 align-top whitespace-nowrap">
                                <div className="font-bold text-slate-500 dark:text-slate-300">{log.timestamp.split(" ")[0]}</div>
                                <div className="text-[10px] mt-0.5">{log.timestamp.split(" ")[1] || ""}</div>
                              </td>

                              {/* Question */}
                              <td className="px-6 py-4 text-slate-800 dark:text-slate-100 align-top break-words max-w-xs font-bold">
                                {log.query}
                              </td>

                              {/* Answer */}
                              <td className="px-6 py-4 text-slate-600 dark:text-slate-300 align-top font-normal max-w-md">
                                <div className="max-h-24 overflow-y-auto text-xs whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-black/10 p-2.5 rounded-xl border border-slate-100 dark:border-white/5 font-semibold">
                                  {log.answer}
                                </div>
                              </td>

                              {/* Model */}
                              <td className="px-6 py-4 align-top whitespace-nowrap">
                                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-extrabold ${isFaq
                                    ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
                                    : log.model.includes("Ollama")
                                      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                      : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                  }`}>
                                  <i className={isFaq ? "fa-solid fa-book" : "fa-solid fa-robot"}></i>
                                  {log.model}
                                </span>
                              </td>

                              {/* Chunk ID */}
                              <td className="px-6 py-4 align-top text-center whitespace-nowrap">
                                {(!log.chunk_ids || log.chunk_ids.length === 0) ? (
                                  <span className="text-slate-400 text-xs">-</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1 justify-center max-w-[120px]">
                                    {log.chunk_ids.map(cid => (
                                      <span key={cid} className="bg-sky-500/10 text-sky-600 dark:text-sky-400 text-[10px] font-extrabold px-1.5 py-0.5 rounded">
                                        #{cid}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>

                              {/* Response Time */}
                              <td className="px-6 py-4 align-top text-right whitespace-nowrap text-slate-700 dark:text-slate-300 font-extrabold text-xs">
                                {isFaq ? (
                                  <span className="text-slate-400 text-xs">0.0 วินาที</span>
                                ) : (
                                  <span>{typeof log.response_time === 'number' ? log.response_time.toFixed(3) : log.response_time} วินาที</span>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB: SATISFACTION STATISTICS */}
          {activeTab === 'satisfaction' && (() => {
            const statsObj = getSatisfactionStatsByPeriod(satPeriod);
            const categoryStats = getCategoryStats(statsObj.filtered);

            return (
              <div className="space-y-6 animate-slide-in">
                {/* Timeframe Selector */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 p-5 rounded-3xl shadow-sm">
                  <div>
                    <h3 className="text-lg font-extrabold flex items-center gap-2">
                      <i className="fa-solid fa-face-smile text-emerald-500"></i> สถิติความพึงพอใจย้อนหลัง
                    </h3>
                    <p className="text-xs text-slate-400 font-semibold mt-1">
                      เลือกช่วงเวลาเพื่อดูสถิติอัตราไลก์/ดิสไลก์ ข้อเสนอแนะ และสถิติแยกตามหมวดหมู่คำถาม
                    </p>
                  </div>

                  {/* Period Switcher Buttons */}
                  <div className="flex items-center bg-slate-100 dark:bg-tuh-navy/55 p-1 rounded-2xl border border-slate-200/50 dark:border-tuh-purple/10">
                    {[
                      { key: 'daily', label: 'รายวัน' },
                      { key: 'weekly', label: 'รายสัปดาห์' },
                      { key: 'monthly', label: 'รายเดือน' },
                      { key: 'yearly', label: 'รายปี' }
                    ].map(p => (
                      <button
                        key={p.key}
                        onClick={() => setSatPeriod(p.key)}
                        className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${satPeriod === p.key ? 'bg-white dark:bg-tuh-purple/35 text-tuh-rose dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'}`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Grid: 4 Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Satisfaction rate */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">อัตราความพึงพอใจ</span>
                      <span className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-sm"><i className="fa-solid fa-circle-check"></i></span>
                    </div>
                    <h3 className={`text-3xl font-black tracking-tight ${statsObj.satRate >= 80 ? 'text-emerald-500' : statsObj.satRate >= 50 ? 'text-amber-500' : 'text-rose-500'}`}>
                      {statsObj.satRate}%
                    </h3>
                    <p className="text-xs text-slate-400 font-semibold mt-1">อัตราความพึงพอใจในรอบ {satPeriod === 'daily' ? '1 วัน' : satPeriod === 'weekly' ? '1 สัปดาห์' : satPeriod === 'monthly' ? '1 เดือน' : '1 ปี'}</p>
                  </div>

                  {/* Likes count */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">ประเมินว่าชอบ (Likes)</span>
                      <span className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-up"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-teal-500">{statsObj.totalLikes}</h3>
                    <p className="text-xs text-slate-400 font-semibold mt-1">จำนวนการตอบกลับเชิงบวก</p>
                  </div>

                  {/* Dislikes count */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">ควรปรับปรุง (Dislikes)</span>
                      <span className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-down"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-rose-500">{statsObj.totalDislikes}</h3>
                    <p className="text-xs text-slate-400 font-semibold mt-1">จำนวนการตอบกลับเชิงลบ</p>
                  </div>

                  {/* Total Feedbacks */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">การประเมินทั้งหมด</span>
                      <span className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-sm"><i className="fa-solid fa-comments"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-indigo-500">{statsObj.totalVotes}</h3>
                    <p className="text-xs text-slate-400 font-semibold mt-1">จำนวนโหวตความพึงพอใจทั้งหมด</p>
                  </div>
                </div>

                {/* Progress bar of Likes vs Dislikes */}
                <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                  <div className="flex justify-between items-center mb-3 text-xs font-bold">
                    <span className="text-teal-500 flex items-center gap-1.5"><i className="fa-solid fa-thumbs-up"></i> ชอบ ({statsObj.totalLikes})</span>
                    <span className="text-rose-500 flex items-center gap-1.5">ควรปรับปรุง ({statsObj.totalDislikes}) <i className="fa-solid fa-thumbs-down"></i></span>
                  </div>
                  <div className="w-full h-4 bg-rose-500/20 dark:bg-rose-500/10 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-emerald-500 transition-all duration-500"
                      style={{ width: `${statsObj.totalVotes > 0 ? (statsObj.totalLikes / statsObj.totalVotes) * 100 : 100}%` }}
                    />
                    <div
                      className="h-full bg-rose-500 transition-all duration-500"
                      style={{ width: `${statsObj.totalVotes > 0 ? (statsObj.totalDislikes / statsObj.totalVotes) * 100 : 0}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-[10px] text-slate-400 font-bold">
                    <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalLikes / statsObj.totalVotes) * 100) : 100}% ของผู้ใช้ประเมินเป็นบวก</span>
                    <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalDislikes / statsObj.totalVotes) * 100) : 0}% ของผู้ใช้ประเมินให้ปรับปรุง</span>
                  </div>
                </div>

                {/* Custom Charts & Category Analysis */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Period chart data representation */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <h3 className="text-base font-extrabold mb-5 flex items-center gap-2">
                      <i className="fa-solid fa-chart-column text-tuh-rose"></i> การแจกแจงความพึงพอใจแยกตาม {satPeriod === 'daily' ? 'ช่วงเวลา' : satPeriod === 'weekly' ? 'วัน' : satPeriod === 'monthly' ? 'สัปดาห์' : 'เดือน'}
                    </h3>

                    <div className="space-y-4">
                      {statsObj.chartData.length === 0 ? (
                        <div className="p-8 text-center text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                          ไม่มีข้อมูลความพึงพอใจในช่วงเวลานี้
                        </div>
                      ) : (
                        statsObj.chartData.map(item => (
                          <div key={item.label} className="space-y-1.5">
                            <div className="flex justify-between items-center text-xs font-semibold">
                              <span className="text-slate-500 dark:text-slate-305">{item.label}</span>
                              <span className="text-slate-400 flex items-center gap-2">
                                <span className="text-teal-500">{item.likes} 👍</span>
                                <span className="text-rose-500">{item.dislikes} 👎</span>
                                <span className="bg-slate-100 dark:bg-black/25 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-extrabold">{item.rate}%</span>
                              </span>
                            </div>
                            <div className="w-full h-2 bg-slate-100 dark:bg-tuh-navy/55 rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all duration-500 ${item.rate >= 80 ? 'bg-teal-500' : item.rate >= 50 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                style={{ width: `${item.total > 0 ? (item.likes / item.total) * 100 : 0}%` }}
                              />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Category Analysis */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <h3 className="text-base font-extrabold mb-5 flex items-center gap-2">
                      <i className="fa-solid fa-tags text-tuh-rose"></i> ความพึงพอใจแยกตามหมวดหมู่คำถามหลัก
                    </h3>

                    <div className="space-y-4">
                      {categoryStats.length === 0 ? (
                        <div className="p-8 text-center text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                          ยังไม่มีคะแนนประเมินที่ตรงกับหมวดหมู่คำถามในช่วงนี้
                        </div>
                      ) : (
                        categoryStats.map(cat => (
                          <div key={cat.name} className="space-y-1.5">
                            <div className="flex justify-between items-center text-xs font-semibold">
                              <span className="text-slate-800 dark:text-slate-100 font-bold">{cat.name}</span>
                              <span className="text-slate-400 flex items-center gap-2">
                                <span className="text-teal-500">{cat.likes} 👍</span>
                                <span className="text-rose-500">{cat.dislikes} 👎</span>
                                <span className="bg-slate-100 dark:bg-black/25 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded font-extrabold">{cat.rate}%</span>
                              </span>
                            </div>
                            <div className="w-full h-2 bg-slate-100 dark:bg-tuh-navy/55 rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all duration-500 ${cat.rate >= 80 ? 'bg-teal-500' : cat.rate >= 50 ? 'bg-amber-500' : 'bg-rose-500'}`}
                                style={{ width: `${cat.total > 0 ? (cat.likes / cat.total) * 100 : 0}%` }}
                              />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* Written Feedbacks/Comments for this period */}
                <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                  <div className="flex justify-between items-center mb-5">
                    <h3 className="text-base font-extrabold flex items-center gap-2">
                      <i className="fa-solid fa-comment-dots text-tuh-rose"></i> ความคิดเห็นและข้อเสนอแนะในช่วงเวลานี้ ({statsObj.comments.length} ข้อความ)
                    </h3>
                  </div>

                  <div className="space-y-3">
                    {statsObj.comments.length === 0 ? (
                      <div className="p-8 text-center text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                        ยังไม่มีข้อเสนอแนะที่เป็นข้อความในช่วงเวลานี้
                      </div>
                    ) : (
                      [...statsObj.comments].reverse().map(c => (
                        <div key={c.id} className="p-4 bg-slate-50 dark:bg-tuh-indigo/20 border border-slate-200/50 dark:border-tuh-purple/10 rounded-2xl flex gap-3.5 items-start">
                          <span className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm ${c.rating === 'like' ? 'bg-teal-500/10 text-teal-500' : 'bg-rose-500/10 text-rose-500'}`}>
                            <i className={`fa-solid ${c.rating === 'like' ? 'fa-thumbs-up' : 'fa-thumbs-down'}`}></i>
                          </span>
                          <div className="min-w-0 flex-1 space-y-1">
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-slate-400 font-bold">{c.timestamp}</span>
                              {c.query && <span className="text-[10px] bg-tuh-pink/40 dark:bg-tuh-purple/25 text-tuh-rose font-bold px-2 py-0.5 rounded-full truncate max-w-[200px]">{c.query}</span>}
                            </div>
                            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 whitespace-pre-wrap">{c.comment}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          {/* TAB 4: FAQS DATABASE */}
          {activeTab === 'faqs' && (
            <div className="space-y-6 animate-slide-in">
              {/* Predefined 6 Home FAQs */}
              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20">
                  <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-circle-question text-tuh-rose"></i> คำถามที่พบบ่อย 6 คำถามหลัก (แสดงเป็นปุ่มบนแชทบอทหน้าแรก)</h3>
                  <p className="text-xs text-slate-400 font-semibold mt-1">คุณสามารถแก้ไขข้อความคำถาม ไอคอน และคำตอบของปุ่มทั้ง 6 ปุ่มที่จะแสดงบนหน้าแรกของแชทบอทฝั่งผู้ใช้ได้ที่นี่</p>
                </div>

                <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(!settings.predefined_faqs || settings.predefined_faqs.length === 0) ? (
                    <div className="col-span-2 p-10 text-center text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-3xl">
                      กำลังโหลดหรือไม่มีรายการคำถามที่พบบ่อย...
                    </div>
                  ) : (
                    settings.predefined_faqs.map(faq => (
                      <div key={faq.id} className="p-4 bg-slate-50 dark:bg-tuh-indigo/25 border border-slate-200/50 dark:border-tuh-purple/15 rounded-2xl flex justify-between items-center hover:border-tuh-rose/30 transition shadow-sm">
                        <div className="space-y-1.5 max-w-[85%]">
                          <h4 className="font-extrabold text-slate-800 dark:text-white flex items-center gap-2 text-[14px]">
                            <span className="w-6 h-6 rounded-lg bg-tuh-pink text-tuh-rose flex items-center justify-center text-xs shrink-0 font-black">
                              <i className={`fa-solid ${faq.icon || 'fa-circle-question'}`}></i>
                            </span>
                            <span className="truncate" title={faq.question}>{faq.question}</span>
                          </h4>
                          <p className="text-xs font-semibold text-slate-500 dark:text-slate-350 pl-8 line-clamp-2 leading-relaxed">
                            {faq.answer || faq.response}
                          </p>
                        </div>
                        <button
                          onClick={() => handleOpenEditPredefinedFaqModal(faq)}
                          className="p-2.5 text-tuh-rose hover:bg-tuh-rose/10 rounded-xl transition flex items-center justify-center shrink-0"
                          title="แก้ไขปุ่ม FAQ นี้"
                        >
                          <i className="fa-solid fa-pen-to-square text-base"></i>
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: SYSTEM CONFIGURATION */}
          {activeTab === 'settings' && (
            <form onSubmit={handleSaveSettings} className="space-y-6 animate-slide-in">
              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm space-y-6">
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
                    <div className="flex justify-between text-xs text-slate-400 font-bold mt-1">
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
                    <div className="flex justify-between text-xs text-slate-400 font-bold mt-1">
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
                    <div className="flex justify-between text-xs text-slate-400 font-bold mt-1">
                      <span>200 (คำตอบสั้นและเร็ว)</span>
                      <span>4000 (คำตอบยาวละเอียด)</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-bold mb-2">เทคโนโลยีการทำ Embedding (Embedding Technology)</label>
                    <div className="w-full bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 font-semibold text-slate-500 dark:text-slate-400 select-none">
                      Local FAISS & BM25 Hybrid Search (รันบนเครื่อง)
                    </div>
                    <div className="text-[10px] text-slate-400 font-semibold mt-1">
                      ระบบประมวลผลและค้นหาข้อมูลแบบไฮบริด (FAISS & BM25) เพื่อความเร็วสูงสุดและไม่ต้องพึ่งพาคลาวด์
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm space-y-6">
                <h3 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-tuh-purple/20 pb-4"><i className="fa-solid fa-message text-tuh-rose"></i> การปรับแต่งประโยคและ System Prompt</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold mb-2">คำกล่าวต้อนรับแรกเริ่มแชท (Welcome Message)</label>
                    <textarea
                      rows="3"
                      value={settings.welcome_message}
                      onChange={(e) => setSettings({ ...settings, welcome_message: e.target.value })}
                      placeholder="เขียนประโยคตอบรับครั้งแรกเมื่อเปิดใช้งานแชทบอท..."
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                    ></textarea>
                  </div>

                  <div>
                    <label className="block text-sm font-bold mb-2">คำสั่งระบบควบคุมพฤติกรรมบอท (System Prompt)</label>
                    <textarea
                      rows="5"
                      value={settings.system_prompt}
                      onChange={(e) => setSettings({ ...settings, system_prompt: e.target.value })}
                      placeholder="เช่น 'คุณคือระบบตอบคำถามสำหรับโรงพยาบาลธรรมศาสตร์...'"
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm leading-relaxed"
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
          )}

          {/* TAB 6: ADMIN PROFILE */}
          {activeTab === 'profile' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-in">

              {/* Profile Card */}
              <div className="p-6 bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm text-center space-y-4">
                <div className="w-24 h-24 rounded-full bg-tuh-gradient-2 mx-auto flex items-center justify-center text-white text-4xl shadow-md">
                  <i className="fa-solid fa-user-tie"></i>
                </div>
                <div>
                  <h3 className="text-xl font-black">{adminUser.name}</h3>
                  <p className="text-xs text-tuh-rose font-black uppercase mt-1 tracking-wider">{adminUser.role}</p>
                </div>
                <div className="border-t border-slate-100 dark:border-tuh-purple/20 pt-4 text-sm text-slate-500 dark:text-slate-400 font-bold space-y-2">
                  <div className="flex justify-between">
                    <span>Username:</span>
                    <span className="text-slate-800 dark:text-white">admin</span>
                  </div>
                  <div className="flex justify-between">
                    <span>อีเมลติดต่อ:</span>
                    <span className="text-slate-800 dark:text-white">{adminUser.email}</span>
                  </div>
                </div>
              </div>

              {/* Password change form */}
              <div className="lg:col-span-2 p-6 bg-white dark:bg-tuh-indigo/40 border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm space-y-6">
                <h3 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-tuh-purple/20 pb-4">
                  <i className="fa-solid fa-shield-halved text-tuh-rose"></i>
                  เปลี่ยนรหัสผ่านแอดมิน (Admin Security)
                </h3>

                <form onSubmit={handleUpdatePassword} className="space-y-4 max-w-md">
                  <div>
                    <label className="block text-sm font-bold mb-2">รหัสผ่านแอดมินใหม่</label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? "text" : "password"}
                        placeholder="ตั้งรหัสผ่านใหม่"
                        required
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 pl-4 pr-12 focus:outline-none focus:border-tuh-rose transition font-semibold"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-350 transition-colors focus:outline-none cursor-pointer"
                      >
                        <i className={`fa-solid ${showNewPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-bold mb-2">ยืนยันรหัสผ่านแอดมินใหม่อีกครั้ง</label>
                    <div className="relative">
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="พิมพ์ยืนยันรหัสผ่านใหม่"
                        required
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 pl-4 pr-12 focus:outline-none focus:border-tuh-rose transition font-semibold"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-4 top-3.5 text-orange-500 hover:text-orange-600 dark:text-orange-400 dark:hover:text-orange-350 transition-colors focus:outline-none cursor-pointer"
                      >
                        <i className={`fa-solid ${showConfirmPassword ? 'fa-eye' : 'fa-eye-slash'}`}></i>
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="inline-flex items-center gap-1.5 bg-tuh-rose hover:bg-tuh-rose/90 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                  >
                    <i className="fa-solid fa-lock-open"></i> เปลี่ยนรหัสผ่านความปลอดภัย
                  </button>
                </form>
              </div>

            </div>
          )}

        </div>
      </main>

      {/* MODAL: ANSWER FAQ MODAL */}
      {showFaqModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-tuh-indigo/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-feather text-tuh-rose"></i> ลงทะเบียนคำตอบตอบกลับ FAQ
              </h3>
              <button
                onClick={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
                className="text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSubmitFaq} className="p-6 space-y-4">
              {currentUnanswered.query && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">คำถามจากผู้ใช้</label>
                  <div className="p-4 bg-slate-100 dark:bg-[#100220]/60 rounded-2xl font-bold border border-slate-200/50 dark:border-tuh-purple/10">
                    {currentUnanswered.query}
                  </div>
                </div>
              )}

              {!currentUnanswered.query && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">คำถามแอดมินตั้งขึ้น</label>
                  <input
                    type="text"
                    required
                    placeholder="พิมพ์ประโยคคำถาม..."
                    value={currentUnanswered.query || ''}
                    onChange={(e) => setCurrentUnanswered({ ...currentUnanswered, query: e.target.value })}
                    className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">เขียนคู่มือคำตอบ (บอทจะตอบประโยคนี้ตรงๆ ทันที)</label>
                <textarea
                  rows="4"
                  required
                  placeholder="เขียนคำตอบที่สั้น กระชับ ตรงประเด็นสำหรับคำถามนี้..."
                  value={faqAnswer}
                  onChange={(e) => setFaqAnswer(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm leading-relaxed"
                ></textarea>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-save mr-1.5"></i> ลงทะเบียนคำตอบสำเร็จ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: EDIT DOC EXCLUDE PAGES MODAL */}
      {showEditDocModal && selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-tuh-indigo/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-file-shield text-tuh-rose"></i> ตั้งค่าหน้าเอกสารละเว้น
              </h3>
              <button
                onClick={() => { setShowEditDocModal(false); setSelectedDoc(null); }}
                className="text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSaveExcludePages} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">ชื่อเอกสาร</label>
                <div className="p-4 bg-slate-100 dark:bg-[#100220]/60 rounded-2xl font-bold border border-slate-200/50 dark:border-tuh-purple/10 text-sm truncate">
                  {selectedDoc.filename}
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">ระบุหมายเลขหน้าที่ต้องการ "ละเว้น" (ไม่นำมาให้บอทตอบ)</label>
                <input
                  type="text"
                  placeholder="เช่น 12, 13, 14, 18 (คั่นด้วยจุลภาค ,)"
                  value={excludePagesInput}
                  onChange={(e) => setExcludePagesInput(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
                <p className="text-xs text-slate-400 font-semibold mt-1.5 leading-relaxed">
                  💡 หน้านโยบายเปล่า, หน้าภาคผนวก, หน้าคำลงท้าย, หรือหน้าปกที่บอทไม่ต้องนำมาสืบค้น สามารถกรอกเพื่อข้ามหน้าเหล่านั้นได้
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowEditDocModal(false); setSelectedDoc(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-floppy-disk mr-1.5"></i> บันทึกตั้งค่าละเว้นหน้า
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* MODAL: EDIT PREDEFINED FAQ MODAL */}
      {showEditPredefinedFaqModal && selectedPredefinedFaq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-tuh-indigo/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-pen-to-square text-tuh-rose"></i> แก้ไขคำถามที่พบบ่อย (ปุ่มหน้าแรก)
              </h3>
              <button
                onClick={() => { setShowEditPredefinedFaqModal(false); setSelectedPredefinedFaq(null); }}
                className="text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSavePredefinedFaq} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">หัวข้อคำถาม (ปุ่ม)</label>
                <input
                  type="text"
                  required
                  placeholder="พิมพ์ประโยคคำถาม..."
                  value={predefinedFaqQuestion}
                  onChange={(e) => setPredefinedFaqQuestion(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowEditPredefinedFaqModal(false); setSelectedPredefinedFaq(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-floppy-disk mr-1.5"></i> บันทึกข้อมูล
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
