import React, { useState, useEffect } from 'react';
import dog from './dog.png'; // Rebuild trigger 
import botAvatar from './bot_avatar.jpg';

const API_URL = `http://${window.location.hostname}:8000`;

const CKEditorWrapper = ({ value, onChange, isDarkMode }) => {
  const containerRef = React.useRef(null);
  const editorRef = React.useRef(null);
  const [isLoaded, setIsLoaded] = React.useState(!!window.CKEDITOR);

  React.useEffect(() => {
    if (window.CKEDITOR) {
      setIsLoaded(true);
      return;
    }

    let script = document.querySelector('script[src="https://cdn.ckeditor.com/4.22.1/full/ckeditor.js"]');
    if (!script) {
      script = document.createElement('script');
      script.src = "https://cdn.ckeditor.com/4.22.1/full/ckeditor.js";
      script.async = true;
      document.head.appendChild(script);
    }

    const onLoad = () => setIsLoaded(true);
    script.addEventListener('load', onLoad);
    return () => {
      script.removeEventListener('load', onLoad);
    };
  }, []);

  React.useEffect(() => {
    if (isLoaded && window.CKEDITOR && containerRef.current) {
      window.CKEDITOR.config.language = 'th';
      window.CKEDITOR.config.allowedContent = true;
      window.CKEDITOR.config.versionCheck = false; // Disable security warnings

      const editor = window.CKEDITOR.replace(containerRef.current, {
        height: 200,
        versionCheck: false,
        removePlugins: 'elementspath',
        toolbar: [
          { name: 'basicstyles', items: ['Bold', 'Italic', 'Underline', 'Strike', '-', 'RemoveFormat'] },
          { name: 'paragraph', items: ['NumberedList', 'BulletedList', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight'] },
          { name: 'links', items: ['Link', 'Unlink'] },
          { name: 'insert', items: ['Table'] }
        ],
        contentsCss: isDarkMode
          ? 'data:text/css,body{background-color:#2c0548 !important;color:#ffffff !important;font-family:sans-serif;padding:10px;}'
          : 'data:text/css,body{background-color:#ffffff !important;color:#0f172a !important;font-family:sans-serif;padding:10px;}'
      });

      editorRef.current = editor;

      // Set initial value
      editor.setData(value || '');

      // Listen to change event
      editor.on('change', () => {
        const data = editor.getData();
        onChange(data);
      });

      return () => {
        if (editor) {
          editor.destroy();
        }
      };
    }
  }, [isLoaded, isDarkMode]);

  React.useEffect(() => {
    if (editorRef.current && editorRef.current.getData() !== value) {
      editorRef.current.setData(value || '');
    }
  }, [value]);

  return (
    <div className="text-black dark:text-black">
      {!isLoaded && <div className="p-4 text-center text-slate-500">กำลังโหลดตัวแก้ไขข้อความ...</div>}
      <textarea ref={containerRef} style={{ display: isLoaded ? 'block' : 'none', visibility: 'hidden' }} />
    </div>
  );
};

function App() {
  let logoutRef = () => { };

  const fetch = (url, options = {}) => {
    const urlStr = typeof url === 'string' ? url : (url.url || '');
    const isLogin = urlStr.includes('/api/admin/login');
    const isFeedbackOrUnansweredSubmit = urlStr.includes('/api/admin/feedback/submit') || urlStr.includes('/api/admin/unanswered/submit');
    const isAdmin = urlStr.includes('/api/admin/');

    if (isAdmin && !isLogin && !isFeedbackOrUnansweredSubmit) {
      const token = localStorage.getItem('tuh_admin_token');
      if (token) {
        options.headers = {
          ...options.headers,
          'Authorization': `Bearer ${token}`
        };
      }
    }

    return window.fetch(url, options).then(res => {
      if (res.status === 401 && isAdmin && !isLogin && !isFeedbackOrUnansweredSubmit) {
        logoutRef();
      }
      return res;
    });
  };

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
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('tuh_admin_active_tab') || 'dashboard';
    }
    return 'dashboard';
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('tuh_admin_active_tab', activeTab);
    }
  }, [activeTab]);

  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 1024);

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

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
    chat_greeting: '',
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

  // AI Query Analysis States
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);

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

  // Pre-upload document options
  const [selectedFileForUpload, setSelectedFileForUpload] = useState(null);
  const [preExcludePages, setPreExcludePages] = useState('');
  const [showPreUploadModal, setShowPreUploadModal] = useState(false);
  // Pipeline states
  const [previewContent, setPreviewContent] = useState('');
  const [previewChunks, setPreviewChunks] = useState([]);
  const [previewFilename, setPreviewFilename] = useState('');
  const [previewModalType, setPreviewModalType] = useState(null); // 'raw' | 'cleaned' | 'chunks'
  const [approvingFilename, setApprovingFilename] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [savingContent, setSavingContent] = useState(false);
  const [originalChunks, setOriginalChunks] = useState([]);
  const [selectedChunkIds, setSelectedChunkIds] = useState(new Set());
  const [expandedChunk, setExpandedChunk] = useState(null);
  const [docSearchQuery, setDocSearchQuery] = useState('');
  const [docSortField, setDocSortField] = useState('upload_date'); // default by upload date
  const [docSortOrder, setDocSortOrder] = useState('desc'); // default desc (newest first)

  // Welfare Forms States
  const [forms, setForms] = useState([]);
  const [formName, setFormName] = useState('');
  const [formFile, setFormFile] = useState(null);
  const [formPage, setFormPage] = useState('');
  const [deleteModalState, setDeleteModalState] = useState({ show: false, type: null, targetId: null, targetName: null });
  const [formSearchQuery, setFormSearchQuery] = useState('');

  // Announcement States
  const [announcements, setAnnouncements] = useState([]);
  const [annTitle, setAnnTitle] = useState('');
  const [annContent, setAnnContent] = useState('');
  const [annStartDate, setAnnStartDate] = useState('');
  const [annEndDate, setAnnEndDate] = useState('');
  const [annFilter, setAnnFilter] = useState('all');
  const [editingAnnId, setEditingAnnId] = useState(null);

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
      fetchForms();
      fetchAnnouncements();
    }
  }, [isLoggedIn]);

  // Refetch history when switching to history tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, isLoggedIn]);

  // Refetch announcements when switching to announcements tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'announcements') {
      fetchAnnouncements();
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

  const handleSort = (field) => {
    if (docSortField === field) {
      setDocSortOrder(docSortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setDocSortField(field);
      setDocSortOrder('desc');
    }
  };

  const handleApproveStep = (filename, currentStatus) => {
    setApprovingFilename(filename);
    fetch(API_URL + '/api/admin/documents/approve', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ filename, current_status: currentStatus })
    })
      .then(res => {
        if (!res.ok) throw new Error("อนุมัติขั้นตอนล้มเหลว");
        return res.json();
      })
      .then(data => {
        showSuccess("อนุมัติขั้นตอนสำเร็จแล้ว!");
        setApprovingFilename(null);
        fetchDocuments();
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาด: ${err.message}`);
        setApprovingFilename(null);
      });
  };

  const handleViewPreview = (filename, type) => {
    setPreviewFilename(filename);
    setPreviewModalType(type);
    setLoadingPreview(true);
    setPreviewContent('');
    setPreviewChunks([]);
    setOriginalChunks([]);
    setSelectedChunkIds(new Set());

    let endpoint = '';
    if (type === 'raw') endpoint = '/api/admin/documents/view_raw';
    else if (type === 'cleaned') endpoint = '/api/admin/documents/view_cleaned';
    else if (type === 'chunks') endpoint = '/api/admin/documents/view_chunks';

    fetch(API_URL + endpoint + `?filename=${encodeURIComponent(filename)}`)
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถดึงข้อมูลพรีวิวได้");
        return res.json();
      })
      .then(data => {
        if (type === 'chunks') {
          const loadedChunks = data.chunks || [];
          setPreviewChunks(loadedChunks);
          setOriginalChunks(JSON.parse(JSON.stringify(loadedChunks))); // deep copy
        } else {
          setPreviewContent(data.content || '');
        }
        setLoadingPreview(false);
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาด: ${err.message}`);
        setLoadingPreview(false);
        setPreviewModalType(null);
      });
  };

  const handleSaveContent = (filename, type, content) => {
    setSavingContent(true);
    fetch(API_URL + '/api/admin/documents/update_content', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ filename, type, content })
    })
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถบันทึกการแก้ไขได้");
        return res.json();
      })
      .then(data => {
        showSuccess("บันทึกการแก้ไขเรียบร้อยแล้ว!");
        setSavingContent(false);
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาดในการบันทึก: ${err.message}`);
        setSavingContent(false);
      });
  };

  const handleSaveIndividualChunk = (filename, chunkId, chunkText) => {
    const updatedChunks = previewChunks.map(c => {
      if (c.chunk_id === chunkId) {
        return { ...c, content: chunkText };
      }
      return c;
    });
    setPreviewChunks(updatedChunks);
    handleSaveContent(filename, 'chunks', updatedChunks);
  };

  const handleSaveSelectedChunks = (filename) => {
    const mergedChunks = originalChunks.map(orig => {
      const edited = previewChunks.find(c => c.chunk_id === orig.chunk_id);
      if (edited && selectedChunkIds.has(orig.chunk_id)) {
        return { ...orig, content: edited.content };
      }
      return orig;
    });

    setSavingContent(true);
    fetch(API_URL + '/api/admin/documents/update_content', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ filename, type: 'chunks', content: mergedChunks })
    })
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถบันทึกการแก้ไขได้");
        return res.json();
      })
      .then(data => {
        showSuccess(`บันทึกรายการที่เลือก (${selectedChunkIds.size} Chunks) เรียบร้อยแล้ว!`);
        setOriginalChunks(JSON.parse(JSON.stringify(mergedChunks)));
        setPreviewChunks(JSON.parse(JSON.stringify(mergedChunks)));
        setSavingContent(false);
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาดในการบันทึก: ${err.message}`);
        setSavingContent(false);
      });
  };

  const handleSaveAllChunks = (filename) => {
    setSavingContent(true);
    fetch(API_URL + '/api/admin/documents/update_content', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ filename, type: 'chunks', content: previewChunks })
    })
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถบันทึกการแก้ไขได้");
        return res.json();
      })
      .then(data => {
        showSuccess("บันทึกส่วนย่อยทั้งหมดเรียบร้อยแล้ว!");
        setOriginalChunks(JSON.parse(JSON.stringify(previewChunks)));
        setSavingContent(false);
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาดในการบันทึก: ${err.message}`);
        setSavingContent(false);
      });
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

  const fetchForms = () => {
    fetch(API_URL + '/api/admin/forms')
      .then(res => res.json())
      .then(data => setForms(data))
      .catch(err => console.error("Error fetching forms:", err));
  };

  const handleAddForm = (e) => {
    e.preventDefault();
    if (!formName.trim()) {
      showError("กรุณากรอกชื่อแบบฟอร์ม");
      return;
    }
    if (!formFile) {
      showError("กรุณาเลือกไฟล์ PDF ของแบบฟอร์ม");
      return;
    }

    const headers = {
      'X-Form-Name': encodeURIComponent(formName),
      'X-File-Name': encodeURIComponent(formFile.name),
      'X-Form-Page': formPage || ''
    };

    fetch(API_URL + '/api/admin/forms/upload', {
      method: 'POST',
      headers: headers,
      body: formFile
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
        } else {
          showSuccess(data.message || "บันทึกและอัปโหลดแบบฟอร์มสำเร็จ");
          setFormName('');
          setFormPage('');
          setFormFile(null);
          const fileInput = document.getElementById('form-file-uploader');
          if (fileInput) fileInput.value = '';
          fetchForms();
        }
      })
      .catch(err => showError("เกิดข้อผิดพลาดในการอัปโหลดแบบฟอร์ม"));
  };

  const confirmDelete = () => {
    if (!deleteModalState.type) return;
    if (deleteModalState.type === 'document') {
      fetch(API_URL + '/api/admin/documents/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: deleteModalState.targetId })
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
        .catch(err => showError("ลบเอกสารไม่สำเร็จ"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    } else if (deleteModalState.type === 'form') {
      fetch(API_URL + '/api/admin/forms/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: deleteModalState.targetId })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            showSuccess("ลบแบบฟอร์มสำเร็จ");
            fetchForms();
          } else {
            showError("ลบไม่สำเร็จ");
          }
        })
        .catch(err => showError("เกิดข้อผิดพลาดในการลบ"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    }
  };



  const fetchAnnouncements = () => {
    fetch(API_URL + '/api/admin/announcements')
      .then(res => res.json())
      .then(data => setAnnouncements(data))
      .catch(err => console.error("Error fetching announcements:", err));
  };

  const handleCreateAnnouncement = (e) => {
    e.preventDefault();
    if (!annTitle.trim() || !annContent.trim() || !annStartDate || !annEndDate) {
      showError("กรุณากรอกข้อมูลให้ครบถ้วนทุกช่อง");
      return;
    }
    if (new Date(annStartDate) > new Date(annEndDate)) {
      showError("วันเริ่มประกาศต้องไม่มากกว่าวันสิ้นสุดประกาศ");
      return;
    }

    const isEdit = editingAnnId !== null;
    const url = isEdit
      ? API_URL + '/api/admin/announcements/update'
      : API_URL + '/api/admin/announcements/create';

    const payload = {
      title: annTitle,
      content: annContent,
      start_date: annStartDate,
      end_date: annEndDate
    };

    if (isEdit) {
      payload.id = editingAnnId;
    }

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          showError(data.error);
        } else {
          showSuccess(isEdit ? "แก้ไขประกาศสำเร็จ" : "สร้างประกาศสำเร็จ");
          setAnnTitle('');
          setAnnContent('');
          setAnnStartDate('');
          setAnnEndDate('');
          setEditingAnnId(null);
          fetchAnnouncements();
        }
      })
      .catch(err => showError(isEdit ? "เกิดข้อผิดพลาดในการแก้ไขประกาศ" : "เกิดข้อผิดพลาดในการสร้างประกาศ"));
  };

  const handleEditAnnouncement = (ann) => {
    setAnnTitle(ann.title);
    setAnnContent(ann.content);
    setAnnStartDate(ann.start_date);
    setAnnEndDate(ann.end_date);
    setEditingAnnId(ann.id);
  };

  const handleCancelEditAnnouncement = () => {
    setAnnTitle('');
    setAnnContent('');
    setAnnStartDate('');
    setAnnEndDate('');
    setEditingAnnId(null);
  };

  const handleDeleteAnnouncement = (annId) => {
    if (!window.confirm("คุณแน่ใจหรือไม่ว่าต้องการลบประกาศนี้ก่อนหมดระยะเวลา?")) return;
    fetch(API_URL + '/api/admin/announcements/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: annId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showSuccess("ลบประกาศสำเร็จ");
          fetchAnnouncements();
        } else {
          showError("ลบไม่สำเร็จ");
        }
      })
      .catch(err => showError("เกิดข้อผิดพลาดในการลบประกาศ"));
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
    if (filteredHistory.length === 0) return;
    const headers = ["เวลาที่ตอบ", "คำถามจากผู้ใช้", "คำตอบที่บอทตอบออกไป", "โมเดล AI", "Chunk ID", "เวลาตอบสนอง (วินาที)"];
    const rows = filteredHistory.map(log => [
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
    if (!logDate) return false;
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
      } else {
        const starsVal = fb.stars !== undefined && fb.stars !== null ? parseInt(fb.stars) : (fb.rating === 'like' ? 5 : 2);
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
    localStorage.removeItem('tuh_admin_active_tab');
    setActiveTab('dashboard');
    setIsLoggedIn(false);
  };
  logoutRef = handleLogout;

  // Auto logout after 10 minutes of inactivity
  useEffect(() => {
    if (!isLoggedIn) return;

    let timeoutId;

    const resetTimer = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        handleLogout();
        showError("เซสชันหมดอายุเนื่องจากไม่มีการใช้งานเกิน 10 นาที");
      }, 10 * 60 * 1000);
    };

    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(event => {
      window.addEventListener(event, resetTimer);
    });

    resetTimer();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      events.forEach(event => {
        window.removeEventListener(event, resetTimer);
      });
    };
  }, [isLoggedIn]);

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

    fetch(API_URL + '/api/admin/password/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => { throw new Error(data.error || "เปลี่ยนรหัสผ่านล้มเหลว") });
        }
        return r.json();
      })
      .then(data => {
        showSuccess("เปลี่ยนรหัสผ่านแอดมินสำเร็จแล้ว (มีผลในการเข้าสู่ระบบครั้งถัดไป)");
        setNewPassword('');
        setConfirmPassword('');
      })
      .catch(err => {
        showError(err.message);
      });
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
    if (log && log.query) {
      setAnalysisLoading(true);
      setAnalysisResult(null);
      fetch(API_URL + '/api/admin/unanswered/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: log.query })
      })
        .then(r => r.json())
        .then(data => {
          setAnalysisResult(data);
          setAnalysisLoading(false);
        })
        .catch(err => {
          console.error("Error analyzing query:", err);
          setAnalysisLoading(false);
        });
    }
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
          answer: predefinedFaqAnswer,
          response: predefinedFaqAnswer,
          icon: predefinedFaqIcon || 'fa-circle-question'
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
  const uploadFile = (file, excludePagesText = '') => {
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
          'X-File-Name': encodeURIComponent(file.name),
          'X-Exclude-Pages': excludePagesText
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
      setSelectedFileForUpload(e.dataTransfer.files[0]);
      setPreExcludePages('');
      setShowPreUploadModal(true);
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
        {/* Floating Light Elements */}
        <div className="absolute top-20 right-20 w-80 h-80 rounded-full bg-tuh-purple/20 blur-[120px] pointer-events-none animate-float-slow"></div>
        <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full bg-tuh-rose/10 blur-[120px] pointer-events-none animate-float-slower"></div>

        <div className="w-full max-w-md bg-white/10 dark:bg-[#2c0548]/25 backdrop-blur-xl p-8 rounded-3xl border border-white/10 shadow-2xl relative z-10 animate-slide-in">
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
                <i className="fa-solid fa-user absolute left-4 top-3.5 text-slate-500 dark:text-slate-400"></i>
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
                <i className="fa-solid fa-lock absolute left-4 top-3.5 text-slate-500 dark:text-slate-400"></i>
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

          <div className="mt-8 text-center text-xs text-slate-500 dark:text-slate-400 font-semibold">
            งานสารสนเทศ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Main View
  return (
    <div className="flex h-screen overflow-hidden bg-[#faf7ff] text-tuh-navy dark:bg-[#100220] dark:text-white transition-colors duration-300 font-sans">

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
      <aside className={`fixed inset-y-0 left-0 z-30 flex flex-col border-r border-slate-200 dark:border-tuh-purple/20 bg-[#f5f0ff] dark:bg-tuh-indigo/90 backdrop-blur-md transition-all duration-300 lg:static lg:translate-x-0 ${isSidebarOpen ? 'w-72 translate-x-0 opacity-100' : 'w-0 -translate-x-full lg:translate-x-0 lg:opacity-0 lg:border-r-0 overflow-hidden'}`}>
        {/* Header */}
        <div className="h-[76px] px-5 border-b border-purple-100 dark:border-tuh-purple/20 flex items-center justify-between gap-3 bg-white dark:bg-tuh-indigo/90">
          <div className="flex items-center gap-3">
            <img
              src={dog}
              alt="TUH Dog Logo"
              className="w-10 h-10 rounded-xl object-cover shadow-md shrink-0 border border-slate-100 dark:border-tuh-purple/20"
            />
            <div>
              <h2
                className="font-extrabold text-tuh-navy dark:text-white leading-tight font-roboto"
                style={{ fontSize: 'calc(1.25rem - 2px)' }}
              >
                TUH Admin Chatbot
              </h2>
              <a
                href="https://intranet.hospital.tu.ac.th/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-tuh-indigo/80 dark:text-slate-200 font-bold block mt-0.5 leading-none transition-colors cursor-pointer font-roboto"
                style={{ fontSize: 'calc(0.8rem - 1px)' }}
              >
                Thammasat University Hospital
              </a>
            </div>
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="p-1 rounded-lg text-tuh-indigo/40 hover:text-tuh-rose hover:bg-slate-100 dark:text-slate-400 dark:hover:text-tuh-pink dark:hover:bg-tuh-indigo/40 transition shrink-0 active:scale-95"
            title="ปิดแถบเมนู"
          >
            <i className="fa-solid fa-chevron-left text-xs"></i>
          </button>
        </div>

        {/* Menu Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto custom-scrollbar">
          <button
            onClick={() => handleTabClick('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'dashboard' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-chart-line text-sm"></i>
            <span>ภาพรวม</span>
          </button>

          <button
            onClick={() => handleTabClick('satisfaction')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'satisfaction' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-face-smile text-sm"></i>
            <span>สถิติความพึงพอใจ</span>
          </button>

          <button
            onClick={() => handleTabClick('documents')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'documents' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-file-pdf text-sm"></i>
            <span>จัดการเอกสาร PDF</span>
          </button>

          <button
            onClick={() => handleTabClick('announcements')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'announcements' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-bullhorn text-sm"></i>
            <span>สร้างและจัดการประกาศ</span>
          </button>

          <button
            onClick={() => handleTabClick('logs')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'logs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <div className="relative">
              <i className="fa-solid fa-circle-question text-sm"></i>
              {stats.pending_unanswered > 0 && (
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse"></span>
              )}
            </div>
            <span>คำถามที่บอทตอบไม่ได้</span>
            {stats.pending_unanswered > 0 && (
              <span className="ml-auto bg-red-500 text-white text-[10px] font-extrabold px-2 py-0.5 rounded-full">
                {stats.pending_unanswered}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabClick('history')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'history' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-clock-rotate-left text-sm"></i>
            <span>ประวัติการตอบของบอท</span>
          </button>

          <button
            onClick={() => handleTabClick('faqs')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'faqs' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-book text-sm"></i>
            <span>คู่มือตอบกลับ (FAQs)</span>
          </button>


          <button
            onClick={() => handleTabClick('profile')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${activeTab === 'profile' ? 'tuh-sidebar-active' : 'tuh-sidebar-inactive font-semibold'}`}
          >
            <i className="fa-solid fa-user-gear text-sm"></i>
            <span>โปรไฟล์แอดมิน</span>
          </button>

          <button
            onClick={() => handleTabClick('settings')}
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
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 dark:bg-white/10 font-bold">
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
        <header className="h-[76px] px-4 md:px-6 border-b border-slate-200 dark:border-tuh-purple/20 bg-white/70 dark:bg-tuh-navy/40 backdrop-blur-md flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2.5 rounded-xl text-tuh-indigo dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-tuh-indigo/50 transition active:scale-95 shrink-0 animate-fade-in"
                title="เปิดแถบเมนู"
              >
                <i className="fa-solid fa-bars text-lg"></i>
              </button>
            )}
            <h1 className="text-xl font-black tracking-tight flex items-center gap-2">
              <span className="text-tuh-rose shrink-0">
                {activeTab === 'dashboard' && <i className="fa-solid fa-chart-line"></i>}
                {activeTab === 'satisfaction' && <i className="fa-solid fa-face-smile"></i>}
                {activeTab === 'documents' && <i className="fa-solid fa-file-pdf"></i>}
                {activeTab === 'announcements' && <i className="fa-solid fa-bullhorn"></i>}
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
                {activeTab === 'announcements' && 'สร้างและจัดการประกาศระบบ'}
                {activeTab === 'logs' && 'บันทึกคำถามที่บอทตอบไม่ได้'}
                {activeTab === 'history' && 'ประวัติการตอบของบอท'}
                {activeTab === 'faqs' && 'ทะเบียนคู่มือคำตอบ FAQs'}
                {activeTab === 'settings' && 'การตั้งค่าระบบ AI แชทบอท'}
                {activeTab === 'profile' && 'โปรไฟล์ผู้ดูแลระบบ'}
              </span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline-flex items-center gap-2 text-sm font-bold px-4 py-2 rounded-full bg-tuh-pink/30 text-tuh-rose border border-tuh-rose/20 dark:bg-tuh-rose/25 dark:text-white dark:border-none shadow-sm">
              <img src={botAvatar} alt="Avatar" className="w-7 h-7 rounded-full object-cover shadow-sm" />
              {adminUser.name} ({adminUser.role})
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
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-sky-500/40 dark:hover:border-sky-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>ประวัติการตอบของบอท</span>
                      <h3 className="text-[30px] font-black tracking-tight text-sky-600 dark:text-sky-400">
                        {stats.total_queries} <span className={`text-[14px] font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>คำถามทั้งหมด</span>
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center text-base"><i className="fa-solid fa-clock-rotate-left"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      บันทึกคิวรีถามตอบของผู้ใช้ย้อนหลัง ความเร็วตอบสนอง และข้อมูลอ้างอิง
                    </p>
                    <span className="text-[14px] text-sky-600 dark:text-sky-400 font-bold flex items-center gap-1">เข้าสู่เมนูประวัติ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 2. Satisfaction Stats Portal */}
                <div
                  onClick={() => setActiveTab('satisfaction')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-emerald-500/40 dark:hover:border-emerald-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>สถิติความพึงพอใจ</span>
                      <h3 className="text-[30px] font-black tracking-tight text-emerald-600 dark:text-emerald-400">
                        {stats.likes + stats.dislikes > 0 ? Math.round((stats.likes / (stats.likes + stats.dislikes)) * 100) : 100}%
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-base"><i className="fa-solid fa-face-smile"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      วิเคราะห์ความพึงพอใจย้อนหลังรายวัน/สัปดาห์/เดือน/ปี และสถิติแยกตามหมวดหมู่คำถามหลัก
                    </p>
                    <span className="text-[14px] text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1">เข้าสู่เมนูสถิติ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 3. Unanswered Logs Portal */}
                <div
                  onClick={() => setActiveTab('logs')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-rose-500/40 dark:hover:border-rose-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>คำถามที่บอทตอบไม่ได้</span>
                      <h3 className={`text-[30px] font-black tracking-tight ${stats.pending_unanswered > 0 ? (isDarkMode ? 'text-[#f06292]' : 'text-rose-600 dark:text-rose-400') : (isDarkMode ? 'text-slate-300' : 'text-slate-600')}`}>
                        {stats.pending_unanswered} <span className={`text-[14px] font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>คำถามค้างตอบ</span>
                      </h3>
                    </div>
                    <span className={`w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-base ${isDarkMode ? 'text-[#f06292]' : 'text-rose-600 dark:text-rose-400'}`}><i className="fa-solid fa-circle-question"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      คำถามจากผู้ใช้ที่บอทไม่มีความรู้อ้างอิง รอการเพิ่มคู่มือคำตอบจากแอดมินโดยตรง
                    </p>
                    <span className={`text-[14px] font-bold flex items-center gap-1 ${isDarkMode ? 'text-[#f06292]' : 'text-rose-600 dark:text-rose-400'}`}>เข้าสู่เมนูตอบคำถาม <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 4. PDF Manage Portal */}
                <div
                  onClick={() => setActiveTab('documents')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-purple-500/40 dark:hover:border-purple-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>จัดการเอกสาร PDF</span>
                      <h3 className={`text-[30px] font-black tracking-tight ${isDarkMode ? 'text-[#f69988]' : 'text-purple-600 dark:text-purple-400'}`}>
                        {stats.active_documents} / {stats.total_documents} <span className={`text-[14px] font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>แฟ้มเปิดใช้งาน</span>
                      </h3>
                    </div>
                    <span className={`w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center text-base ${isDarkMode ? 'text-[#f69988]' : 'text-purple-600 dark:text-purple-400'}`}><i className="fa-solid fa-file-pdf"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      อัปโหลดแฟ้มข้อมูล PDF ค้นหา ลบ และจัดการสิทธิ์การข้ามบางหน้าของการเรียนรู้ของระบบ RAG
                    </p>
                    <span className={`text-[14px] font-bold flex items-center gap-1 ${isDarkMode ? 'text-[#f69988]' : 'text-purple-600 dark:text-purple-400'}`}>เข้าสู่เมนูจัดการไฟล์ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 5. FAQs Portal */}
                <div
                  onClick={() => setActiveTab('faqs')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-amber-500/40 dark:hover:border-amber-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>คู่มือตอบกลับ (FAQs)</span>
                      <h3 className="text-[30px] font-black tracking-tight text-amber-600 dark:text-amber-400">
                        {settings.predefined_faqs?.length || 0} <span className={`text-[14px] font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>คำถามด่วนหน้าแรก</span>
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center text-base"><i className="fa-solid fa-book"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      จัดการไอคอน คำถาม และคำตอบด่วนสำหรับการคลิกถามยอดฮิต {settings.predefined_faqs?.length || 0} ปุ่มบนหน้าแรกของผู้ใช้
                    </p>
                    <span className="text-[14px] text-amber-600 dark:text-amber-400 font-bold flex items-center gap-1">เข้าสู่เมนู FAQs <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
                  </div>
                </div>

                {/* 6. System Announcements Portal */}
                <div
                  onClick={() => setActiveTab('announcements')}
                  className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm hover:shadow-lg hover:border-pink-500/40 dark:hover:border-pink-500/50 hover:translate-y-[-2px] active:scale-95 transition-all duration-300 cursor-pointer flex flex-col justify-between min-h-[12rem] h-auto pb-4"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <span className={`text-[14px] font-bold uppercase tracking-wider ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>สร้างและจัดการประกาศ</span>
                      <h3 className="text-[30px] font-black tracking-tight text-pink-600 dark:text-pink-400">
                        {announcements.filter(ann => {
                          const now = new Date();
                          return now >= new Date(ann.start_date) && now <= new Date(ann.end_date);
                        }).length} / {announcements.length} <span className={`text-[14px] font-bold ${isDarkMode ? 'text-slate-300' : 'text-slate-700 dark:text-slate-300'}`}>เปิดใช้งาน</span>
                      </h3>
                    </div>
                    <span className="w-10 h-10 rounded-xl bg-pink-500/10 text-pink-600 dark:text-pink-400 flex items-center justify-center text-base"><i className="fa-solid fa-bullhorn"></i></span>
                  </div>
                  <div className="space-y-2 mt-3">
                    <p className={`text-[14px] font-semibold leading-relaxed line-clamp-2 ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
                      สร้างข่าวประชาสัมพันธ์ ตั้งเวลาแสดงผล และเปิด/ปิดป้ายประกาศข่าวสารถึงผู้ใช้แชทบอท
                    </p>
                    <span className="text-[14px] text-pink-600 dark:text-pink-400 font-bold flex items-center gap-1">เข้าสู่เมนูจัดการประกาศ <i className="fa-solid fa-arrow-right text-[10px]"></i></span>
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
                  : 'border-slate-300 dark:border-tuh-purple/30 bg-white dark:bg-[#2c0548]/25'
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
                      <p className="text-sm text-slate-500 dark:text-slate-400 font-bold mt-1">ระบบรองรับไฟล์ระเบียบและเอกสารภาษาไทยนามสกุล PDF เท่านั้น</p>
                    </div>
                    <div>
                      <input
                        type="file"
                        id="pdf-uploader"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setSelectedFileForUpload(e.target.files[0]);
                            setPreExcludePages('');
                            setShowPreUploadModal(true);
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
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-wrap">
                    <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-table text-tuh-rose"></i> แฟ้มเอกสารทั้งหมด</h3>
                    {stats.last_build_duration !== undefined && stats.last_build_duration !== null && (
                      <span className="text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-black/20 px-3.5 py-1.5 rounded-full border border-slate-200/50 dark:border-tuh-purple/10">
                        ⏱️ สกัดเวกเตอร์ล่าสุดเสร็จสิ้นใน {stats.last_build_duration.toFixed(2)} วินาที
                      </span>
                    )}
                  </div>
                  {/* Search Bar */}
                  <div className="relative w-full md:w-72">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-slate-500 dark:text-slate-400">
                      <i className="fa-solid fa-magnifying-glass text-xs"></i>
                    </span>
                    <input
                      type="text"
                      placeholder="ค้นหาเอกสารตามชื่อไฟล์..."
                      value={docSearchQuery}
                      onChange={(e) => setDocSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-4 py-2.5 text-xs font-bold bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl focus:outline-none focus:border-tuh-rose transition text-tuh-navy dark:text-white"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20 select-none">
                        <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('filename')}>
                          ชื่อไฟล์
                          {docSortField === 'filename' ? (
                            docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                          ) : (
                            <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                          )}
                        </th>
                        <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('size')}>
                          ขนาดไฟล์
                          {docSortField === 'size' ? (
                            docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                          ) : (
                            <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                          )}
                        </th>
                        <th className="px-6 py-4 text-center cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('pages')}>
                          จำนวนหน้า
                          {docSortField === 'pages' ? (
                            docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                          ) : (
                            <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                          )}
                        </th>
                        <th className="px-6 py-4 cursor-pointer hover:text-tuh-rose transition" onClick={() => handleSort('upload_date')}>
                          วันที่อัปโหลด
                          {docSortField === 'upload_date' ? (
                            docSortOrder === 'asc' ? <i className="fa-solid fa-arrow-up text-[10px] ml-1 text-tuh-rose"></i> : <i className="fa-solid fa-arrow-down text-[10px] ml-1 text-tuh-rose"></i>
                          ) : (
                            <i className="fa-solid fa-arrows-up-down text-[9px] ml-1 text-slate-300 dark:text-slate-600"></i>
                          )}
                        </th>
                        <th className="px-6 py-4 text-center">สถานะการทำงาน</th>
                        <th className="px-6 py-4 text-center">เปิดใช้งาน</th>
                        <th className="px-6 py-4 text-right">เครื่องมือ</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                      {(() => {
                        const filtered = documents.filter(doc =>
                          doc.filename.toLowerCase().includes(docSearchQuery.toLowerCase())
                        );

                        const sorted = [...filtered].sort((a, b) => {
                          let valA = a[docSortField];
                          let valB = b[docSortField];

                          if (docSortField === 'size' || docSortField === 'pages') {
                            valA = valA || 0;
                            valB = valB || 0;
                          } else if (docSortField === 'filename' || docSortField === 'upload_date') {
                            valA = (valA || '').toLowerCase();
                            valB = (valB || '').toLowerCase();
                          }

                          if (valA < valB) return docSortOrder === 'asc' ? -1 : 1;
                          if (valA > valB) return docSortOrder === 'asc' ? 1 : -1;
                          return 0;
                        });

                        if (sorted.length === 0) {
                          return (
                            <tr>
                              <td colSpan="7" className="px-6 py-8 text-center text-slate-500 dark:text-slate-400 font-bold">
                                {documents.length === 0 ? 'ไม่มีไฟล์เอกสารที่บันทึกไว้ในขณะนี้' : 'ไม่พบเอกสารที่ตรงกับการค้นหา'}
                              </td>
                            </tr>
                          );
                        }

                        return sorted.map(doc => {
                          const isProcessing = doc.status === 'Processing';
                          const isActive = doc.status === 'Active';
                          const isPipeline = ['Step_Raw_Text', 'Step_Clean_Text', 'Step_Chunk_Preview'].includes(doc.status);
                          return (
                            <tr key={doc.filename} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              <td className="px-6 py-4 font-bold max-w-[200px] truncate text-tuh-navy dark:text-white" title={doc.filename}>
                                <i className="fa-solid fa-file-pdf text-red-500 mr-2"></i>
                                {doc.filename}
                              </td>
                              <td className="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400">
                                {Math.round(doc.size / 1024)} KB
                              </td>
                              <td className="px-6 py-4 text-center text-tuh-navy dark:text-slate-200">
                                <div>{doc.pages || '-'} หน้า</div>
                                {doc.exclude_pages && doc.exclude_pages.length > 0 && (
                                  <div className="text-[10px] text-red-500 font-bold bg-red-500/10 rounded-full px-2 py-0.5 inline-block mt-1">
                                    ละเว้นหน้า: {doc.exclude_pages.join(', ')}
                                  </div>
                                )}
                              </td>
                              <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                                {doc.upload_date}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isProcessing ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-500">
                                    <i className="fa-solid fa-circle-notch animate-spin"></i>
                                    กำลังปรับปรุงฐานข้อมูล
                                  </span>
                                ) : doc.status === 'Error' ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/10 text-red-500">
                                    <i className="fa-solid fa-circle-xmark"></i>
                                    ผิดพลาด
                                  </span>
                                ) : isPipeline ? (
                                  <div className="flex flex-col items-center">
                                    <div className="flex items-center gap-1 justify-center mt-1">
                                      <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Raw_Text' ? 'bg-amber-500 text-white animate-pulse' : 'bg-emerald-500 text-white'
                                        }`} title="สกัดข้อความดิบ">1</div>
                                      <div className={`w-4 h-0.5 ${doc.status !== 'Step_Raw_Text' ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                        }`} />
                                      <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Clean_Text' ? 'bg-amber-500 text-white animate-pulse' : (doc.status === 'Step_Chunk_Preview' || doc.status === 'Active') ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                        }`} title="คลีนข้อมูล">2</div>
                                      <div className={`w-4 h-0.5 ${(doc.status === 'Step_Chunk_Preview' || doc.status === 'Active') ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                        }`} />
                                      <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Step_Chunk_Preview' ? 'bg-amber-500 text-white animate-pulse' : doc.status === 'Active' ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                        }`} title="แบ่งข้อมูล">3</div>
                                      <div className={`w-4 h-0.5 ${doc.status === 'Active' ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-white/10'
                                        }`} />
                                      <div className={`flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-extrabold ${doc.status === 'Active' ? 'bg-emerald-500 text-white' : 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-slate-400'
                                        }`} title="เวกเตอร์ทำงาน">4</div>
                                    </div>
                                    <div className="text-[10px] font-bold text-amber-500 mt-1">
                                      {doc.status === 'Step_Raw_Text' && '1. ตรวจคำดิบ'}
                                      {doc.status === 'Step_Clean_Text' && '2. ตรวจคำคลีน'}
                                      {doc.status === 'Step_Chunk_Preview' && '3. ตรวจส่วนย่อย (Chunk)'}
                                    </div>
                                  </div>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500">
                                    <i className="fa-solid fa-circle-check"></i>
                                    พร้อมใช้งาน
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isPipeline ? (
                                  <span className="text-xs font-bold text-amber-500 bg-amber-500/10 rounded-full px-2.5 py-1 inline-flex items-center gap-1">
                                    <i className="fa-solid fa-hourglass-half animate-spin"></i> รอนุมัติ
                                  </span>
                                ) : (
                                  /* Status Toggle Switch */
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
                                )}
                              </td>
                              <td className="px-6 py-4 text-right flex items-center justify-end gap-1.5">
                                {isPipeline ? (
                                  <>
                                    {/* Preview Content Button */}
                                    <button
                                      onClick={() => {
                                        if (doc.status === 'Step_Raw_Text') handleViewPreview(doc.filename, 'raw');
                                        if (doc.status === 'Step_Clean_Text') handleViewPreview(doc.filename, 'cleaned');
                                        if (doc.status === 'Step_Chunk_Preview') handleViewPreview(doc.filename, 'chunks');
                                      }}
                                      className="inline-flex items-center gap-1 bg-sky-500 hover:bg-sky-600 text-white font-bold py-1.5 px-3 rounded-xl text-xs hover:shadow transition active:scale-95"
                                      title="ตรวจสอบเนื้อหาขั้นตอนนี้"
                                    >
                                      <i className="fa-solid fa-eye text-[11px]"></i> พรีวิว
                                    </button>
                                    {/* Approve Button */}
                                    <button
                                      disabled={approvingFilename === doc.filename}
                                      onClick={() => handleApproveStep(doc.filename, doc.status)}
                                      className="inline-flex items-center gap-1 bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-1.5 px-3 rounded-xl text-xs hover:shadow transition active:scale-95 disabled:opacity-50"
                                      title="อนุมัติเข้าสู่ขั้นตอนถัดไป"
                                    >
                                      {approvingFilename === doc.filename ? (
                                        <i className="fa-solid fa-spinner animate-spin"></i>
                                      ) : (
                                        <i className="fa-solid fa-circle-check text-[11px]"></i>
                                      )}
                                      อนุมัติ
                                    </button>
                                  </>
                                ) : null}
                                <button
                                  disabled={approvingFilename === doc.filename}
                                  onClick={() => setDeleteModalState({ show: true, type: 'document', targetId: doc.filename, targetName: doc.filename })}
                                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-xl transition active:scale-95 flex items-center justify-center disabled:opacity-50"
                                  title="ลบเอกสาร"
                                >
                                  <i className="fa-solid fa-trash-can text-sm"></i>
                                </button>
                              </td>
                            </tr>
                          );
                        });
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Welfare Forms Management Panel */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
                {/* 1. Add Form Panel */}
                <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm">
                  <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2 mb-4">
                    <i className="fa-solid fa-file-circle-plus text-tuh-rose"></i> เพิ่มแบบฟอร์มสวัสดิการ
                  </h3>
                  <form onSubmit={handleAddForm} className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ชื่อแบบฟอร์ม <span className="text-red-500">*</span></label>
                      <input
                        type="text"
                        required
                        placeholder="เช่น แบบเสนอขอรับสวัสดิการ..."
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                        className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">อัปโหลดไฟล์แบบฟอร์ม (PDF) <span className="text-red-500">*</span></label>
                      <input
                        type="file"
                        id="form-file-uploader"
                        required
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setFormFile(e.target.files[0]);
                          }
                        }}
                        className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เลือกหน้าที่ต้องการตัดจาก PDF</label>
                      <input
                        type="text"
                        placeholder="เช่น 3 หรือ 1,3,5 หรือ 2-5 (ระบบจะตัดเฉพาะหน้าที่เลือกให้ User โหลด)"
                        value={formPage}
                        onChange={(e) => setFormPage(e.target.value)}
                        className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center justify-center gap-2 mt-2"
                    >
                      <i className="fa-solid fa-cloud-arrow-up"></i> บันทึกและอัปโหลดไฟล์
                    </button>
                  </form>
                </div>

                {/* 2. Forms List Panel */}
                <div className="lg:col-span-2 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm flex flex-col">
                  <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2">
                      <i className="fa-solid fa-folder-open text-tuh-rose"></i> แฟ้มแบบฟอร์มทั้งหมด ({forms.length} รายการ)
                    </h3>
                    {/* Search Bar for Forms */}
                    <div className="relative w-full md:w-60">
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-500 dark:text-slate-400">
                        <i className="fa-solid fa-magnifying-glass text-xs"></i>
                      </span>
                      <input
                        type="text"
                        placeholder="ค้นหาชื่อแบบฟอร์ม..."
                        value={formSearchQuery}
                        onChange={(e) => setFormSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 text-xs font-bold bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl focus:outline-none focus:border-tuh-rose transition text-tuh-navy dark:text-white"
                      />
                    </div>
                  </div>

                  <div className="flex-1 overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                          <th className="px-6 py-3.5">ชื่อแบบฟอร์ม</th>
                          <th className="px-6 py-3.5">ไฟล์ PDF / หน้าที่ระบุ</th>
                          <th className="px-6 py-3.5 text-center">ดาวน์โหลด</th>
                          <th className="px-6 py-3.5 text-right">จัดการ</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                        {(() => {
                          const filtered = forms.filter(form =>
                            form.name.toLowerCase().includes(formSearchQuery.toLowerCase())
                          );

                          if (filtered.length === 0) {
                            return (
                              <tr>
                                <td colSpan="4" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-bold">
                                  {forms.length === 0 ? 'ยังไม่มีแบบฟอร์มที่ลงทะเบียนไว้ในแฟ้มข้อมูล' : 'ไม่พบแบบฟอร์มที่ตรงกับการค้นหา'}
                                </td>
                              </tr>
                            );
                          }

                          return filtered.map((form) => (
                            <tr key={form.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              <td className="px-6 py-4 font-bold text-tuh-navy dark:text-white">
                                <i className="fa-regular fa-file-lines text-teal-500 mr-2"></i>
                                {form.name}
                              </td>
                              <td className="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400">
                                <div className="flex flex-col gap-0.5">
                                  <span className="truncate max-w-[180px] block text-tuh-navy dark:text-slate-200" title={form.filename ? form.filename.substring(form.filename.indexOf('_') + 1) : ''}>
                                    <i className="fa-solid fa-file-pdf text-red-500 mr-1.5"></i>
                                    {form.filename ? form.filename.substring(form.filename.indexOf('_') + 1) : 'ไม่มีไฟล์'}
                                  </span>
                                  {form.page && <span className="text-sm font-extrabold text-tuh-rose">หน้า {form.page}</span>}
                                </div>
                              </td>
                              <td className="px-6 py-4 text-center">
                                <a
                                  href={form.page ? `${form.link}#page=${form.page}` : form.link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 transition"
                                  title="เปิดดู / ดาวน์โหลดเอกสาร PDF"
                                >
                                  <i className="fa-solid fa-arrow-down-long text-xs"></i>
                                </a>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <button
                                  onClick={() => setDeleteModalState({ show: true, type: 'form', targetId: form.id, targetName: form.name })}
                                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-xl transition active:scale-95 inline-flex items-center justify-center"
                                  title="ลบแบบฟอร์ม"
                                >
                                  <i className="fa-solid fa-trash-can text-sm"></i>
                                </button>
                              </td>
                            </tr>
                          ));
                        })()}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB: ANNOUNCEMENTS */}
          {activeTab === 'announcements' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-in">
              {/* Form to create/edit announcement */}
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm h-fit">
                <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2 mb-4">
                  <i className="fa-solid fa-bullhorn text-tuh-rose"></i> {editingAnnId ? "แก้ไขประกาศ" : "สร้างประกาศใหม่"}
                </h3>
                <form onSubmit={handleCreateAnnouncement} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เรื่อง / หัวข้อประกาศ</label>
                    <input
                      type="text"
                      placeholder="กรอกหัวข้อประกาศ..."
                      value={annTitle}
                      onChange={(e) => setAnnTitle(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เนื้อหาประกาศ</label>
                    <CKEditorWrapper
                      value={annContent}
                      onChange={(data) => setAnnContent(data)}
                      isDarkMode={isDarkMode}
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">วันและเวลาเริ่มแสดงประกาศ</label>
                    <input
                      type="datetime-local"
                      value={annStartDate}
                      onChange={(e) => setAnnStartDate(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">วันและเวลาสิ้นสุดประกาศ</label>
                    <input
                      type="datetime-local"
                      value={annEndDate}
                      onChange={(e) => setAnnEndDate(e.target.value)}
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-2.5 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm text-tuh-navy dark:text-white"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <button
                      type="submit"
                      className="w-full bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center justify-center gap-2 mt-2"
                    >
                      <i className="fa-solid fa-check-circle"></i> {editingAnnId ? "ยืนยันการแก้ไขประกาศ" : "ยืนยันการสร้างประกาศ"}
                    </button>
                    {editingAnnId && (
                      <button
                        type="button"
                        onClick={handleCancelEditAnnouncement}
                        className="w-full bg-slate-100 dark:bg-[#100220]/45 hover:bg-slate-200 dark:hover:bg-tuh-purple/10 text-slate-700 dark:text-slate-200 font-bold py-2.5 px-6 rounded-2xl transition active:scale-[0.98] flex items-center justify-center gap-2"
                      >
                        ยกเลิกการแก้ไข
                      </button>
                    )}
                  </div>
                </form>
              </div>

              {/* Announcements List */}
              <div className="lg:col-span-2 space-y-4">
                <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-5 shadow-sm">
                  <h3 className="text-base font-extrabold text-tuh-navy dark:text-white flex items-center gap-2 mb-4">
                    <i className="fa-solid fa-list-check text-tuh-rose"></i> รายการประกาศทั้งหมด ({announcements.length})
                  </h3>

                  {/* Status Filter Tabs */}
                  <div className="flex flex-wrap gap-1.5 mb-4 bg-slate-50 dark:bg-tuh-navy/20 p-1.5 rounded-2xl w-fit">
                    <button
                      onClick={() => setAnnFilter('all')}
                      className={`px-4 py-1.5 rounded-xl text-xs font-bold transition ${annFilter === 'all' ? 'bg-tuh-gradient-2 text-white shadow-sm' : 'text-slate-500 dark:text-slate-350 hover:bg-slate-100 dark:hover:bg-tuh-purple/10'}`}
                    >
                      ทั้งหมด ({announcements.length})
                    </button>
                    <button
                      onClick={() => setAnnFilter('active')}
                      className={`px-4 py-1.5 rounded-xl text-xs font-bold transition ${annFilter === 'active' ? 'bg-emerald-500 text-white shadow-sm' : 'text-slate-500 dark:text-slate-350 hover:bg-slate-100 dark:hover:bg-tuh-purple/10'}`}
                    >
                      ดำเนินการ ({announcements.filter(ann => {
                        const now = new Date();
                        return now >= new Date(ann.start_date) && now <= new Date(ann.end_date);
                      }).length})
                    </button>
                    <button
                      onClick={() => setAnnFilter('expired')}
                      className={`px-4 py-1.5 rounded-xl text-xs font-bold transition ${annFilter === 'expired' ? 'bg-slate-400 text-white shadow-sm' : 'text-slate-500 dark:text-slate-350 hover:bg-slate-100 dark:hover:bg-tuh-purple/10'}`}
                    >
                      หมดระยะเวลา ({announcements.filter(ann => {
                        const now = new Date();
                        return now > new Date(ann.end_date);
                      }).length})
                    </button>
                    <button
                      onClick={() => setAnnFilter('pending')}
                      className={`px-4 py-1.5 rounded-xl text-xs font-bold transition ${annFilter === 'pending' ? 'bg-amber-500 text-white shadow-sm' : 'text-slate-500 dark:text-slate-350 hover:bg-slate-100 dark:hover:bg-tuh-purple/10'}`}
                    >
                      รอแสดงผล ({announcements.filter(ann => {
                        const now = new Date();
                        return now < new Date(ann.start_date);
                      }).length})
                    </button>
                  </div>

                  {announcements.length === 0 ? (
                    <div className="text-center py-12 text-slate-400 dark:text-slate-300 font-bold">
                      <i className="fa-solid fa-bullhorn text-4xl mb-3 block opacity-30"></i>
                      ไม่มีประกาศในระบบขณะนี้
                    </div>
                  ) : (() => {
                    const filteredAnnouncements = announcements.filter((ann) => {
                      const now = new Date();
                      const start = new Date(ann.start_date);
                      const end = new Date(ann.end_date);
                      if (annFilter === 'active') {
                        return now >= start && now <= end;
                      } else if (annFilter === 'expired') {
                        return now > end;
                      } else if (annFilter === 'pending') {
                        return now < start;
                      }
                      return true;
                    });

                    if (filteredAnnouncements.length === 0) {
                      return (
                        <div className="text-center py-12 text-slate-400 dark:text-slate-300 font-bold">
                          <i className="fa-solid fa-filter-circle-xmark text-4xl mb-3 block opacity-30"></i>
                          ไม่มีประกาศตามเงื่อนไขตัวกรองที่เลือก
                        </div>
                      );
                    }

                    return (
                      <div className="grid grid-cols-1 gap-4">
                        {filteredAnnouncements.map((ann) => {
                          const now = new Date();
                          const start = new Date(ann.start_date);
                          const end = new Date(ann.end_date);
                          let statusBadge = null;

                          if (now < start) {
                            statusBadge = <span className="bg-amber-500/10 text-amber-500 border border-amber-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold">รอแสดงผล</span>;
                          } else if (now > end) {
                            statusBadge = <span className="bg-slate-500/10 text-slate-400 border border-slate-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold">หมดระยะเวลา</span>;
                          } else {
                            statusBadge = <span className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 px-2.5 py-0.5 rounded-full text-xs font-bold animate-pulse">กำลังแสดงผล</span>;
                          }

                          return (
                            <div key={ann.id} className="p-5 rounded-2xl border border-slate-100 dark:border-tuh-purple/10 bg-slate-50/50 dark:bg-tuh-navy/20 flex flex-col justify-between gap-4 hover:shadow-md transition">
                              <div className="flex justify-between items-start gap-4">
                                <div className="space-y-1.5 flex-1">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <h4 className="font-extrabold text-tuh-navy dark:text-white text-base">{ann.title}</h4>
                                    {statusBadge}
                                  </div>
                                  <div
                                    className="text-sm font-semibold text-slate-650 dark:text-slate-350 leading-relaxed html-content"
                                    dangerouslySetInnerHTML={{ __html: ann.content }}
                                  />
                                </div>
                                <div className="flex gap-1 shrink-0">
                                  <button
                                    onClick={() => handleEditAnnouncement(ann)}
                                    className="p-2 rounded-xl text-tuh-purple dark:text-tuh-purple-400 hover:bg-tuh-purple/10 transition active:scale-95"
                                    title="แก้ไขประกาศ"
                                  >
                                    <i className="fa-solid fa-pen-to-square text-lg"></i>
                                  </button>
                                  <button
                                    onClick={() => handleDeleteAnnouncement(ann.id)}
                                    className="p-2 rounded-xl text-red-500 hover:bg-red-500/10 hover:text-red-650 transition active:scale-95"
                                    title="ลบประกาศ"
                                  >
                                    <i className="fa-solid fa-trash-can text-lg"></i>
                                  </button>
                                </div>
                              </div>

                              <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-300 border-t border-slate-100 dark:border-tuh-purple/5 pt-3 font-semibold gap-2">
                                <div>
                                  <i className="fa-regular fa-clock mr-1"></i>
                                  เริ่ม: {ann.start_date.replace("T", " ")} | สิ้นสุด: {ann.end_date.replace("T", " ")}
                                </div>
                                <div>
                                  สร้างเมื่อ: {ann.created_at}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: UNANSWERED LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-6 animate-slide-in">
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20">
                  <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-triangle-exclamation text-tuh-rose"></i> รายชื่อคำถามที่บอทตอบไม่ได้</h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
                        <th className="px-6 py-4">ข้อความคำถาม</th>
                        <th className="px-6 py-4 text-center">ถามซ้ำ (จำนวน)</th>
                        <th className="px-6 py-4 whitespace-nowrap">ถามล่าสุดเมื่อ</th>
                        <th className="px-6 py-4 text-center">สถานะ</th>
                        <th className="px-6 py-4 text-center">เครื่องมือแก้ไข</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-tuh-purple/10 text-sm font-semibold">
                      {unanswered.length === 0 ? (
                        <tr>
                          <td colSpan="5" className="px-6 py-8 text-center text-slate-500 dark:text-slate-400 font-bold">
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
                              <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                                {log.timestamp}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isPending ? (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-500 dark:text-rose-400 border border-rose-500/20 dark:border-rose-400/20 whitespace-nowrap">
                                    <i className="fa-solid fa-clock-rotate-left"></i>
                                    ค้างตอบ
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500 whitespace-nowrap">
                                    <i className="fa-solid fa-circle-check"></i>
                                    แก้ไขแล้ว
                                  </span>
                                )}
                              </td>
                              <td className="px-6 py-4 text-center">
                                {isPending && (
                                  <div className="flex items-center justify-center gap-2 whitespace-nowrap">
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
                                  </div>
                                )}
                                {!isPending && (
                                  <button
                                    onClick={() => handleResolveUnanswered(log.id, "Pending")}
                                    className="text-xs text-rose-500 dark:text-rose-400 hover:underline whitespace-nowrap"
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
                <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex items-center justify-between col-span-1">
                  <div className="space-y-1">
                    <span className="text-[15px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">คำถามทั้งหมดที่โดนถาม</span>
                    <h3 className="text-3xl font-black tracking-tight text-sky-500">
                      {filteredHistory.length} <span className="text-[15px] font-bold text-slate-500 dark:text-slate-400">คำถาม</span>
                    </h3>
                    <p className="text-[13px] text-slate-500 dark:text-slate-400 font-semibold">
                      จากคำถามสะสมทั้งหมด {history.length} ในฐานข้อมูล
                    </p>
                  </div>
                  <span className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-500 flex items-center justify-center text-xl shrink-0"><i className="fa-solid fa-comments"></i></span>
                </div>

                {/* Period Switcher Card */}
                <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex flex-col justify-between col-span-2">
                  <div>
                    <span className="text-[15px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ฟิลเตอร์สลับช่วงเวลาบันทึกประวัติ</span>
                    <p className="text-[15px] text-slate-500 dark:text-slate-400 font-semibold mt-1">เลือกช่วงเวลาเพื่อปรับการแสดงสถิติจำนวนคำถามและการแสดงตารางรายละเอียดด้านล่าง</p>
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
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-extrabold flex items-center gap-2">
                      <i className="fa-solid fa-clock-rotate-left text-tuh-rose"></i> ตารางรายการประวัติการตอบของบอท
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
                      บันทึกรายการคำถาม-คำตอบ อ้างอิงตามระยะเวลาที่เลือก (ดาวน์โหลด CSV เพื่อส่งออกข้อมูลตามฟิลเตอร์ที่เลือก)
                    </p>
                  </div>
                  <div className="flex items-center gap-2 self-start md:self-auto">
                    <button
                      onClick={downloadCSV}
                      disabled={filteredHistory.length === 0}
                      className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-xl active:scale-[0.98] transition flex items-center gap-2 text-xs shadow-sm hover:shadow"
                    >
                      <i className="fa-solid fa-file-csv"></i> ดาวน์โหลด CSV
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse min-w-[800px]">
                    <thead>
                      <tr className="bg-slate-100 dark:bg-tuh-navy/30 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-tuh-purple/20">
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
                          <td colSpan="6" className="px-6 py-12 text-center text-slate-500 font-bold">
                            <div className="inline-block w-6 h-6 border-2 border-tuh-rose border-t-transparent rounded-full animate-spin mr-2"></div>
                            กำลังโหลดประวัติ...
                          </td>
                        </tr>
                      ) : filteredHistory.length === 0 ? (
                        <tr>
                          <td colSpan="6" className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-bold">
                            ไม่มีประวัติการตอบคำถามในช่วงเวลาที่เลือก
                          </td>
                        </tr>
                      ) : (
                        filteredHistory.map((log) => {
                          const isFaq = log.model === "Direct FAQ";
                          return (
                            <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-tuh-indigo/10 transition">
                              {/* Time */}
                              <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 align-top whitespace-nowrap">
                                <div className="font-bold text-slate-500 dark:text-slate-300">{log.timestamp.split(" ")[0]}</div>
                                <div className="text-[10px] mt-0.5">{log.timestamp.split(" ")[1] || ""}</div>
                              </td>

                              {/* Question */}
                              <td className="px-6 py-4 text-slate-800 dark:text-slate-100 align-top break-words max-w-xs font-bold">
                                {log.query}
                              </td>

                              {/* Answer */}
                              <td className="px-6 py-4 text-slate-600 dark:text-slate-300 align-top font-normal max-w-md">
                                <div className="max-h-64 overflow-y-auto text-xs whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-black/10 p-2.5 rounded-xl border border-slate-100 dark:border-white/5 font-semibold">
                                  {log.answer}
                                </div>
                              </td>

                              {/* Model */}
                              <td className="px-6 py-4 align-top whitespace-nowrap">
                                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-extrabold ${isFaq
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
                                  <span className="text-slate-500 dark:text-slate-400 text-xs">-</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1 justify-center max-w-[120px]">
                                    {log.chunk_ids.map(cid => (
                                      <span key={cid} className="bg-sky-500/10 text-sky-600 dark:text-sky-400 text-xs font-extrabold px-1.5 py-0.5 rounded">
                                        #{cid}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>

                              {/* Response Time */}
                              <td className="px-6 py-4 align-top text-right whitespace-nowrap text-slate-700 dark:text-slate-300 font-extrabold text-xs">
                                {isFaq ? (
                                  <span className="text-slate-500 dark:text-slate-400 text-xs">0.0 วินาที</span>
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
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
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
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">พึงพอใจการตอบคำถาม</span>
                      <span className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-sm"><i className="fa-solid fa-circle-check"></i></span>
                    </div>
                    <h3 className={`text-3xl font-black tracking-tight ${statsObj.satRate >= 80 ? 'text-emerald-500' : statsObj.satRate >= 50 ? 'text-amber-500' : 'text-rose-500'}`}>
                      {statsObj.satRate}%
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">อัตราความพึงพอใจคำตอบรอบนี้</p>
                  </div>

                  {/* Likes count */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ถูกใจคำตอบ (Likes)</span>
                      <span className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-up"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-teal-500">{statsObj.totalLikes}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนที่กดถูกใจคำตอบบอท</p>
                  </div>

                  {/* Dislikes count */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ไม่ถูกใจคำตอบ (Dislikes)</span>
                      <span className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center text-sm"><i className="fa-solid fa-thumbs-down"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-rose-500">{statsObj.totalDislikes}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนที่กดไม่ถูกใจคำตอบบอท</p>
                  </div>

                  {/* Total Feedbacks */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">การประเมินคำตอบทั้งหมด</span>
                      <span className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-sm"><i className="fa-solid fa-comments"></i></span>
                    </div>
                    <h3 className="text-3xl font-black tracking-tight text-indigo-500">{statsObj.totalVotes}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">จำนวนโหวตคำตอบบอททั้งหมด</p>
                  </div>
                </div>

                {/* Grid: Likes vs Dislikes progress AND Star Ratings */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Progress bar of Likes vs Dislikes */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex flex-col justify-between">
                    <div>
                      <h3 className="text-base font-extrabold mb-4 flex items-center gap-2">
                        <i className="fa-solid fa-thumbs-up text-teal-500"></i> สัดส่วนความพึงพอใจต่อคำตอบของแชทบอท
                      </h3>
                      <div className="flex justify-between items-center mb-3 text-xs font-bold">
                        <span className="text-teal-500 flex items-center gap-1.5"><i className="fa-solid fa-thumbs-up"></i> ถูกใจ ({statsObj.totalLikes})</span>
                        <span className="text-rose-500 flex items-center gap-1.5">ไม่ถูกใจ ({statsObj.totalDislikes}) <i className="fa-solid fa-thumbs-down"></i></span>
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
                    </div>
                    <div className="flex justify-between mt-4 text-[10px] text-slate-500 dark:text-slate-400 font-bold pt-3 border-t border-slate-100 dark:border-tuh-purple/10">
                      <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalLikes / statsObj.totalVotes) * 100) : 100}% ประเมินเป็นบวก</span>
                      <span>{statsObj.totalVotes > 0 ? Math.round((statsObj.totalDislikes / statsObj.totalVotes) * 100) : 0}% ประเมินควรปรับปรุง</span>
                    </div>
                  </div>

                  {/* Star rating distribution (Overall experience) */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-base font-extrabold flex items-center gap-2">
                        <i className="fa-solid fa-star text-amber-500"></i> ระดับคะแนนดาวประเมินบริการภาพรวม ({statsObj.totalStarsCount} การประเมิน)
                      </h3>
                      {statsObj.totalStarsCount > 0 && (
                        <span className="text-sm font-black text-amber-500 bg-amber-500/10 px-2.5 py-1 rounded-xl border border-amber-500/20">
                          {(
                            (statsObj.starCounts[5] * 5 +
                              statsObj.starCounts[4] * 4 +
                              statsObj.starCounts[3] * 3 +
                              statsObj.starCounts[2] * 2 +
                              statsObj.starCounts[1] * 1) /
                            statsObj.totalStarsCount
                          ).toFixed(1)}{' '}
                          / 5.0
                        </span>
                      )}
                    </div>
                    <div className="space-y-2.5">
                      {[5, 4, 3, 2, 1].map((star) => {
                        const count = statsObj.starCounts[star] || 0;
                        const percentage = statsObj.totalStarsCount > 0 ? Math.round((count / statsObj.totalStarsCount) * 100) : 0;
                        return (
                          <div key={star} className="flex items-center gap-4 text-xs font-bold">
                            <span className="w-12 text-slate-500 dark:text-slate-400 flex items-center gap-1">
                              {star} ดาว <i className="fa-solid fa-star text-amber-400 text-[10px]"></i>
                            </span>
                            <div className="flex-1 h-3 bg-slate-100 dark:bg-tuh-indigo/20 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-amber-400 transition-all duration-500"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                            <span className="w-16 text-right text-slate-700 dark:text-slate-200">
                              {count} คน ({percentage}%)
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Grid: 2 Comment Cards */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Comments from Thumbs-Down clicks */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex flex-col">
                    <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-100 dark:border-tuh-purple/10">
                      <h3 className="text-base font-extrabold flex items-center gap-2">
                        <i className="fa-solid fa-thumbs-down text-rose-500"></i> รายงานข้อเสนอแนะคำตอบที่ควรปรับปรุง ({statsObj.dislikeComments.length} ข้อความ)
                      </h3>
                    </div>

                    <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                      {statsObj.dislikeComments.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                          ยังไม่มีข้อเสนอแนะจากคำตอบที่ควรปรับปรุงในช่วงเวลานี้
                        </div>
                      ) : (
                        [...statsObj.dislikeComments].reverse().map(c => (
                          <div key={c.id} className="p-4 bg-slate-50 dark:bg-tuh-indigo/10 border border-slate-200/50 dark:border-tuh-purple/10 rounded-2xl flex gap-3 items-start shadow-sm hover:shadow-md transition duration-200">
                            <span className="w-9 h-9 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center shrink-0 text-base">
                              <i className="fa-solid fa-thumbs-down"></i>
                            </span>
                            <div className="min-w-0 flex-1 space-y-2">
                              <div className="flex justify-between items-center pb-1.5 border-b border-slate-100 dark:border-tuh-purple/10">
                                <span className="text-xs text-slate-500 dark:text-slate-400 font-bold flex items-center gap-1">
                                  <i className="fa-regular fa-clock"></i> {c.timestamp}
                                </span>
                              </div>

                              <div className="space-y-2 text-sm leading-relaxed">
                                {c.query && (
                                  <div className="space-y-1">
                                    <span className="text-xs font-black text-indigo-500 dark:text-indigo-400 flex items-center gap-1.5">
                                      <i className="fa-solid fa-circle-question"></i> คำถามของผู้ใช้:
                                    </span>
                                    <p className="bg-white dark:bg-black/15 p-3 rounded-xl border border-slate-100 dark:border-tuh-purple/5 font-semibold text-slate-700 dark:text-slate-200 text-sm">
                                      {c.query}
                                    </p>
                                  </div>
                                )}
                                {c.answer && (
                                  <div className="space-y-1">
                                    <span className="text-xs font-black text-rose-500 flex items-center gap-1.5">
                                      <i className="fa-solid fa-robot"></i> คำตอบจากบอท:
                                    </span>
                                    <p className="bg-rose-500/5 dark:bg-rose-500/10 p-3 rounded-xl border border-rose-500/10 font-semibold text-slate-600 dark:text-slate-300 text-sm whitespace-pre-wrap">
                                      {c.answer}
                                    </p>
                                  </div>
                                )}
                                <div className="space-y-1">
                                  <span className="text-xs font-black text-teal-600 dark:text-teal-400 flex items-center gap-1.5">
                                    <i className="fa-solid fa-comment-dots"></i> เหตุผลที่ควรปรับปรุง:
                                  </span>
                                  <p className="bg-slate-100/80 dark:bg-tuh-indigo/20 p-3 rounded-xl border border-slate-200/50 dark:border-tuh-purple/10 font-bold text-slate-800 dark:text-white text-sm whitespace-pre-wrap">
                                    {c.comment}
                                  </p>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Comments from Star Ratings */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm flex flex-col">
                    <div className="flex justify-between items-center mb-5 pb-3 border-b border-slate-100 dark:border-tuh-purple/10">
                      <h3 className="text-base font-extrabold flex items-center gap-2">
                        <i className="fa-solid fa-star text-amber-500"></i> ความคิดเห็นจากคะแนนดาวภาพรวม ({statsObj.starComments.length} ข้อความ)
                      </h3>
                    </div>

                    <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                      {statsObj.starComments.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                          ยังไม่มีความคิดเห็นจากคะแนนดาวในช่วงเวลานี้
                        </div>
                      ) : (
                        [...statsObj.starComments].reverse().map(c => {
                          const starsVal = c.stars !== undefined && c.stars !== null ? c.stars : (c.rating === 'like' ? 5 : 2);
                          return (
                            <div key={c.id} className="p-4 bg-slate-50 dark:bg-tuh-indigo/10 border border-slate-200/50 dark:border-tuh-purple/10 rounded-2xl flex gap-3 items-start shadow-sm hover:shadow-md transition duration-200">
                              <span className="w-16 px-1.5 py-1.5 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center gap-1 font-black text-xs shrink-0 border border-amber-500/20">
                                <i className="fa-solid fa-star"></i> {starsVal} ดาว
                              </span>
                              <div className="min-w-0 flex-1 space-y-2">
                                <div className="flex justify-between items-center pb-1.5 border-b border-slate-100 dark:border-tuh-purple/10">
                                  <span className="text-xs text-slate-500 dark:text-slate-400 font-bold flex items-center gap-1">
                                    <i className="fa-regular fa-clock"></i> {c.timestamp}
                                  </span>
                                </div>
                                <div className="space-y-1">
                                  <p className="bg-white dark:bg-black/15 p-3 rounded-xl border border-slate-100 dark:border-tuh-purple/5 font-bold text-slate-800 dark:text-white whitespace-pre-wrap text-sm">
                                    {c.comment}
                                  </p>
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>

                {/* Custom Charts */}
                <div className="w-full">
                  {/* Period chart data representation */}
                  <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm">
                    <h3 className="text-base font-extrabold mb-5 flex items-center gap-2">
                      <i className="fa-solid fa-chart-column text-tuh-rose"></i> การแจกแจงความพึงพอใจแยกตาม {satPeriod === 'daily' ? 'ช่วงเวลา' : satPeriod === 'weekly' ? 'วัน' : satPeriod === 'monthly' ? 'สัปดาห์' : 'เดือน'}
                    </h3>

                    <div className="space-y-4">
                      {statsObj.chartData.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-2xl">
                          ไม่มีข้อมูลความพึงพอใจในช่วงเวลานี้
                        </div>
                      ) : (
                        statsObj.chartData.map(item => (
                          <div key={item.label} className="space-y-1.5">
                            <div className="flex justify-between items-center text-xs font-semibold">
                              <span className="text-slate-500 dark:text-slate-305">{item.label}</span>
                              <span className="text-slate-500 dark:text-slate-400 flex items-center gap-2">
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
                </div>
              </div>
            );
          })()}

          {/* TAB 4: FAQS DATABASE */}
          {activeTab === 'faqs' && (
            <div className="space-y-6 animate-slide-in">
              {/* Predefined 6 Home FAQs */}
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 dark:border-tuh-purple/20">
                  <h3 className="text-lg font-extrabold flex items-center gap-2"><i className="fa-solid fa-circle-question text-tuh-rose"></i> คำถามที่พบบ่อย 4 คำถามหลัก (แสดงเป็นปุ่มบนแชทบอทหน้าแรก)</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">คุณสามารถแก้ไขข้อความคำถาม ไอคอน และคำตอบของปุ่มทั้ง 4 ปุ่มที่จะแสดงบนหน้าแรกของแชทบอทฝั่งผู้ใช้ได้ที่นี่</p>
                </div>

                <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(!settings.predefined_faqs || settings.predefined_faqs.length === 0) ? (
                    <div className="col-span-2 p-10 text-center text-slate-500 dark:text-slate-400 font-bold border border-dashed border-slate-200 dark:border-tuh-purple/20 rounded-3xl">
                      กำลังโหลดหรือไม่มีรายการคำถามที่พบบ่อย...
                    </div>
                  ) : (
                    settings.predefined_faqs.map(faq => (
                      <div key={faq.id} className="p-4 bg-slate-50 dark:bg-[#2c0548]/25 border border-slate-200/50 dark:border-tuh-purple/15 rounded-2xl flex justify-between items-center hover:border-tuh-rose/30 transition shadow-sm">
                        <div className="space-y-1.5 max-w-[85%]">
                          <h4 className="font-extrabold text-slate-800 dark:text-white flex items-center gap-2 text-[14px]">
                            <span className="w-6 h-6 rounded-lg bg-tuh-pink text-tuh-rose flex items-center justify-center text-xs shrink-0 font-black">
                              <i className={`fa-solid ${faq.icon || 'fa-circle-question'}`}></i>
                            </span>
                            <span className="truncate" title={faq.question}>{faq.question}</span>
                          </h4>
                          <p className="text-xs font-semibold text-slate-500 dark:text-slate-350 pl-8 line-clamp-2 leading-relaxed">
                            {faq.answer || faq.response || <span className="italic text-slate-400 font-medium">(ค้นหาคำตอบอัตโนมัติจากไฟล์ PDF)</span>}
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
              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm space-y-6">
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
                      Local FAISS & BM25 Hybrid Search (รันบนเครื่อง)
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 font-semibold mt-1">
                      ระบบประมวลผลและค้นหาข้อมูลแบบไฮบริด (FAISS & BM25) เพื่อความเร็วสูงสุดและไม่ต้องพึ่งพาคลาวด์
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl p-6 shadow-sm space-y-6">
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
                    <label className="block text-sm font-bold mb-2">คำทักทายเริ่มต้นบทสนทนาใหม่ในแชท (Chat Greeting)</label>
                    <textarea
                      rows="3"
                      value={settings.chat_greeting}
                      onChange={(e) => setSettings({ ...settings, chat_greeting: e.target.value })}
                      placeholder="เขียนประโยคทักทายครั้งแรกในห้องแชท..."
                      className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                    ></textarea>
                  </div>

                  <div>
                    <label className="block text-sm font-bold mb-2">คำสั่งระบบควบคุมพฤติกรรมบอท (System Prompt)</label>
                    <textarea
                      rows="12"
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
              <div className="p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm text-center space-y-4">
                <div className="w-24 h-24 rounded-full mx-auto shadow-md overflow-hidden border-4 border-white dark:border-tuh-purple/30 bg-slate-100 flex items-center justify-center">
                  <img src={botAvatar} alt="Admin Profile" className="w-full h-full object-cover" />
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
              <div className="lg:col-span-2 p-6 bg-white dark:bg-[#2c0548] border border-slate-200 dark:border-tuh-purple/20 rounded-3xl shadow-sm space-y-6">
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
          <div className="w-full max-w-lg bg-white dark:bg-[#2c0548]/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-feather text-tuh-rose"></i> ลงทะเบียนคำตอบตอบกลับ FAQ
              </h3>
              <button
                onClick={() => { setShowFaqModal(false); setCurrentUnanswered(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSubmitFaq} className="p-6 space-y-4">
              {currentUnanswered.query && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามจากผู้ใช้</label>
                  <div className="p-4 bg-slate-100 dark:bg-[#100220]/60 rounded-2xl font-bold border border-slate-200/50 dark:border-tuh-purple/10">
                    {currentUnanswered.query}
                  </div>
                </div>
              )}

              {!currentUnanswered.query && (
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">คำถามแอดมินตั้งขึ้น</label>
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

              {/* AI Query Analysis Recommendations */}
              {(analysisLoading || analysisResult) && (
                <div className="p-4 rounded-2xl border border-dashed border-tuh-purple/20 bg-slate-50 dark:bg-[#100220]/25 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <i className="fa-solid fa-wand-magic-sparkles text-tuh-rose animate-pulse"></i>
                      วิเคราะห์ประโยคและคำค้นหาแนะนำโดย AI
                    </span>
                    {analysisLoading && (
                      <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1.5">
                        <i className="fa-solid fa-spinner animate-spin text-[10px]"></i> กำลังวิเคราะห์...
                      </span>
                    )}
                  </div>

                  {analysisResult && (
                    <div className="space-y-2">
                      {analysisResult.is_valid_query === false ? (
                        <div className="text-xs font-semibold text-rose-500 dark:text-rose-455 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20">
                          ⚠️ AI ประเมินว่าเป็นข้อความขยะหรือคำทักทายทั่วไป (ไม่ใช่คำถามเกี่ยวกับสวัสดิการ)
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="flex flex-wrap gap-1.5">
                            {analysisResult.suggested_keywords && analysisResult.suggested_keywords.map((kw, i) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => {
                                  navigator.clipboard.writeText(kw);
                                  showSuccess(`คัดลอกคำว่า "${kw}" แล้ว`);
                                }}
                                className="px-2.5 py-1 text-xs font-bold rounded-lg bg-tuh-rose/10 text-tuh-rose hover:bg-tuh-rose/20 transition active:scale-95 flex items-center gap-1"
                              >
                                {kw}
                                <i className="fa-regular fa-copy text-[10px] opacity-60"></i>
                              </button>
                            ))}
                          </div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-450 font-semibold">
                            💡 คลิกที่คำสำคัญแนะนำด้านบนเพื่อคัดลอกและนำไปใช้ในการแต่งประโยค FAQ เพื่อการค้นหาที่แม่นยำขึ้น
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">เขียนคู่มือคำตอบ (บอทจะตอบประโยคนี้ตรงๆ ทันที)</label>
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



      {/* MODAL: CUSTOM CONFIRM DELETE MODAL */}
      {deleteModalState.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md bg-white dark:bg-[#1C1950] rounded-3xl border border-slate-200 dark:border-2 dark:border-[#93ABD9] shadow-2xl overflow-hidden p-6 text-center animate-scale-up">
            <div className="w-16 h-16 rounded-full bg-[#E97D30]/15 dark:bg-[#E7BEF8]/20 text-[#E97D30] dark:text-[#F2619C] text-3xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#E97D30]/10 dark:shadow-[#F2619C]/10">
              <i className="fa-solid fa-triangle-exclamation animate-bounce"></i>
            </div>
            <h3 className="text-xl font-black text-slate-900 dark:text-white mb-2.5">
              {deleteModalState.type === 'document' ? 'ยืนยันการลบเอกสาร' : 'ยืนยันการลบแบบฟอร์ม'}
            </h3>
            <p className="text-sm font-semibold text-slate-600 dark:text-slate-200 mb-6 leading-relaxed whitespace-pre-line">
              คุณแน่ใจหรือไม่ว่าต้องการลบ <span className="font-extrabold text-[#E97D30] dark:text-[#F2619C]">"{deleteModalState.targetName}"</span>?
              {deleteModalState.type === 'document' && '\nข้อมูลใน Vector Index ของเอกสารนี้จะถูกนำออกทั้งหมด'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setDeleteModalState({ show: false, type: null, targetId: null, targetName: null })}
                className="px-6 py-2.5 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-[#93ABD9] dark:hover:opacity-90 dark:text-white font-bold transition active:scale-95 text-sm"
              >
                ยกเลิก
              </button>
              <button
                onClick={confirmDelete}
                className="px-6 py-2.5 rounded-2xl bg-[#E97D30] dark:bg-[#F2619C] hover:opacity-90 text-white font-bold transition active:scale-[0.98] shadow-lg shadow-[#E97D30]/25 dark:shadow-[#F2619C]/25 text-sm"
              >
                ลบ
              </button>
            </div>
          </div>
        </div>
      )}


      {/* MODAL: PRE-UPLOAD CONFIGURE EXCLUDE PAGES MODAL */}
      {showPreUploadModal && selectedFileForUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-[#2c0548]/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-file-circle-plus text-tuh-rose"></i> ตั้งค่าการนำเข้าและละเว้นหน้า
              </h3>
              <button
                onClick={() => { setShowPreUploadModal(false); setSelectedFileForUpload(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setShowPreUploadModal(false);
                uploadFile(selectedFileForUpload, preExcludePages);
                setSelectedFileForUpload(null);
              }}
              className="p-6 space-y-4"
            >
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">ไฟล์ที่เลือก</label>
                <div className="p-4 bg-slate-100 dark:bg-[#100220]/60 rounded-2xl font-bold border border-slate-200/50 dark:border-tuh-purple/10 text-sm truncate text-tuh-navy dark:text-white">
                  {selectedFileForUpload.name}
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-200 mb-1.5">
                  ระบุหมายเลขหน้าที่ต้องการ "ละเว้น" (ถ้ามี)
                </label>
                <input
                  type="text"
                  placeholder="ระบุเลขหน้า เช่น 12, 13, 14, 18 (คั่นด้วยจุลภาค ,) หรือปล่อยว่างไว้"
                  value={preExcludePages}
                  onChange={(e) => setPreExcludePages(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-tuh-navy dark:text-white"
                />
                <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1.5 leading-relaxed">
                  💡 หน้านโยบายเปล่า, หน้าภาคผนวก, หน้าคำลงท้าย, หรือหน้าปกที่บอทไม่ต้องนำมาสืบค้น สามารถกรอกเพื่อข้ามหน้าเหล่านั้นได้ตั้งแต่แรก
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowPreUploadModal(false); setSelectedFileForUpload(null); }}
                  className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98]"
                >
                  <i className="fa-solid fa-cloud-arrow-up mr-1.5"></i> เริ่มอัปโหลดและประมวลผล
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: PIPELINE WORKFLOW CONTENT PREVIEW MODAL */}
      {previewModalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-4xl bg-white dark:bg-[#2c0548]/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-square-poll-horizontal text-tuh-rose"></i>
                ตรวจสอบและแก้ไขข้อมูล: {previewFilename}
                <span className="text-xs bg-amber-500/10 text-amber-500 py-1 px-3 rounded-full font-bold ml-2">
                  {previewModalType === 'raw' && 'ขั้นตอนที่ 1: คำดิบจาก PDF (สามารถแก้ไขได้)'}
                  {previewModalType === 'cleaned' && 'ขั้นตอนที่ 2: ข้อความหลังคลีน (Markdown) (สามารถแก้ไขได้)'}
                  {previewModalType === 'chunks' && 'ขั้นตอนที่ 3: ส่วนย่อยสำหรับสืบค้น (Chunks) (สามารถแก้ไขได้)'}
                </span>
              </h3>
              <button
                onClick={() => { setPreviewModalType(null); setPreviewFilename(''); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div className="p-6">
              {loadingPreview ? (
                <div className="py-20 flex flex-col items-center justify-center space-y-4">
                  <div className="w-12 h-12 rounded-full border-4 border-tuh-rose border-t-transparent animate-spin"></div>
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-bold">กำลังดึงข้อมูลพรีวิว...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {previewModalType === 'chunks' ? (
                    <div>
                      {/* Selective Saving Toolbar */}
                      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-100/80 dark:bg-tuh-navy/30 p-3 rounded-2xl border border-slate-200/50 dark:border-tuh-purple/10 mb-3 text-xs font-bold">
                        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-300">
                          <i className="fa-solid fa-list-check text-tuh-rose"></i>
                          <span>เลือกแล้ว: <strong className="text-tuh-rose">{selectedChunkIds.size}</strong> จาก <strong>{previewChunks.length}</strong> Chunks</span>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            type="button"
                            onClick={() => setSelectedChunkIds(new Set(previewChunks.map(c => c.chunk_id)))}
                            className="px-3 py-1.5 bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 rounded-xl transition active:scale-95 text-slate-700 dark:text-slate-200"
                          >
                            เลือกทั้งหมด
                          </button>
                          <button
                            type="button"
                            onClick={() => setSelectedChunkIds(new Set())}
                            className="px-3 py-1.5 bg-slate-200 dark:bg-white/10 hover:bg-slate-300 dark:hover:bg-white/20 rounded-xl transition active:scale-95 text-slate-700 dark:text-slate-200"
                          >
                            ล้างการเลือก
                          </button>
                          <button
                            type="button"
                            disabled={selectedChunkIds.size === 0 || savingContent}
                            onClick={() => handleSaveSelectedChunks(previewFilename)}
                            className="px-3.5 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl hover:shadow transition active:scale-95 flex items-center gap-1 disabled:opacity-50 disabled:pointer-events-none"
                          >
                            <i className="fa-solid fa-save"></i> บันทึกรายการที่เลือก
                          </button>
                          <button
                            type="button"
                            disabled={savingContent}
                            onClick={() => handleSaveAllChunks(previewFilename)}
                            className="px-3.5 py-1.5 bg-sky-500 hover:bg-sky-600 text-white rounded-xl hover:shadow transition active:scale-95 flex items-center gap-1 disabled:opacity-50"
                          >
                            <i className="fa-solid fa-square-check"></i> บันทึกทั้งหมด
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto max-h-[50vh] pr-1">
                        {previewChunks.map((c, i) => (
                          <div key={i} className={`p-4 bg-slate-50 dark:bg-[#100220]/60 border rounded-2xl flex flex-col space-y-2 hover:border-tuh-rose/30 transition ${selectedChunkIds.has(c.chunk_id) ? 'border-tuh-rose/50 dark:border-tuh-rose/40 shadow-sm' : 'border-slate-200/50 dark:border-tuh-purple/10'}`}>
                            <div className="flex justify-between items-center text-xs font-bold text-slate-500 dark:text-slate-400">
                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={selectedChunkIds.has(c.chunk_id)}
                                  onChange={(e) => {
                                    const newSet = new Set(selectedChunkIds);
                                    if (e.target.checked) {
                                      newSet.add(c.chunk_id);
                                    } else {
                                      newSet.delete(c.chunk_id);
                                    }
                                    setSelectedChunkIds(newSet);
                                  }}
                                  className="w-4 h-4 text-tuh-rose border-slate-300 rounded focus:ring-tuh-rose cursor-pointer"
                                />
                                <span className="text-tuh-navy dark:text-white">Chunk #{c.chunk_id || (i + 1)}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <span className="bg-tuh-rose/10 text-tuh-rose px-2 py-0.5 rounded-full text-[10px]">
                                  หน้า {c.metadata?.page || 1}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => setExpandedChunk(c)}
                                  className="p-1 text-slate-500 dark:text-slate-400 hover:text-tuh-rose hover:bg-slate-100/50 dark:hover:bg-white/10 rounded-lg transition"
                                  title="ขยายขนาดกล่องข้อความ"
                                >
                                  <i className="fa-solid fa-expand text-xs"></i>
                                </button>
                              </div>
                            </div>

                            <div className="flex flex-col space-y-1.5 h-full">
                              <textarea
                                value={c.content}
                                onChange={(e) => {
                                  const newText = e.target.value;
                                  const updated = [...previewChunks];
                                  updated[i] = { ...c, content: newText };
                                  setPreviewChunks(updated);

                                  // Auto check on edit
                                  if (!selectedChunkIds.has(c.chunk_id)) {
                                    const newSet = new Set(selectedChunkIds);
                                    newSet.add(c.chunk_id);
                                    setSelectedChunkIds(newSet);
                                  }
                                }}
                                className="w-full h-28 p-3 text-xs text-tuh-navy/90 dark:text-slate-200 leading-relaxed font-semibold bg-white dark:bg-[#100220]/45 border border-slate-200/50 dark:border-tuh-purple/10 rounded-xl focus:outline-none focus:border-tuh-rose transition resize-none"
                                placeholder="เนื้อหาข้อมูลส่วนย่อย..."
                              />
                              <div className="flex justify-between items-center pt-1.5 border-t border-slate-100 dark:border-white/5">
                                <span className="text-[10px] text-slate-500 dark:text-slate-400 font-bold">
                                  📏 {c.content?.length || 0} ตัวอักษร
                                </span>
                                <button
                                  disabled={savingContent}
                                  onClick={() => handleSaveIndividualChunk(previewFilename, c.chunk_id, c.content)}
                                  className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-lg text-[10px] transition active:scale-95 disabled:opacity-50"
                                  title="บันทึกเฉพาะ Chunk นี้"
                                >
                                  {savingContent ? (
                                    <i className="fa-solid fa-spinner animate-spin"></i>
                                  ) : (
                                    <i className="fa-solid fa-save text-[9px]"></i>
                                  )}
                                  บันทึก Chunk
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-xs font-bold text-slate-500 dark:text-slate-400 mb-2">
                        {previewModalType === 'raw' ? '📝 แก้ไขข้อมูลตัวอักษรดิบที่สกัดจากหน้าเอกสาร:' : '📝 แก้ไขข้อมูลมาร์กดาวน์หลังแปลงรูปแบบและแปลงเลขไทย:'}
                      </div>
                      <textarea
                        value={previewContent}
                        onChange={(e) => setPreviewContent(e.target.value)}
                        className="w-full h-[55vh] p-5 font-mono text-xs leading-relaxed border border-slate-200/50 dark:border-slate-700 rounded-2xl bg-slate-50 text-slate-800 dark:bg-[#100220] dark:text-slate-200 focus:outline-none focus:border-tuh-rose transition resize-none custom-scrollbar"
                        placeholder="กรอก/แก้ไขเนื้อหาเอกสารที่นี่..."
                      />
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-6 border-t border-slate-100 dark:border-tuh-purple/20 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setPreviewModalType(null); setPreviewFilename(''); }}
                className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
              >
                ปิดหน้าต่าง
              </button>
              {previewModalType !== 'chunks' && (
                <button
                  type="button"
                  disabled={savingContent}
                  onClick={() => handleSaveContent(previewFilename, previewModalType, previewContent)}
                  className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
                >
                  {savingContent ? (
                    <i className="fa-solid fa-spinner animate-spin"></i>
                  ) : (
                    <i className="fa-solid fa-save"></i>
                  )}
                  บันทึกการแก้ไข
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SUB-MODAL FOR EXPANDED/ZOOMED CHUNK EDITING */}
      {expandedChunk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
          <div className="w-full max-w-3xl bg-white dark:bg-[#2c0548]/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h4 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-expand text-tuh-rose"></i>
                แก้ไขคำอธิบายส่วนย่อย: Chunk #{expandedChunk.chunk_id} (หน้า {expandedChunk.metadata?.page || 1})
              </h4>
              <button
                onClick={() => setExpandedChunk(null)}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <div className="p-6 space-y-4">
              <textarea
                value={expandedChunk.content}
                onChange={(e) => {
                  const newText = e.target.value;
                  setExpandedChunk({ ...expandedChunk, content: newText });

                  const idx = previewChunks.findIndex(x => x.chunk_id === expandedChunk.chunk_id);
                  if (idx !== -1) {
                    const updated = [...previewChunks];
                    updated[idx] = { ...updated[idx], content: newText };
                    setPreviewChunks(updated);

                    if (!selectedChunkIds.has(expandedChunk.chunk_id)) {
                      const newSet = new Set(selectedChunkIds);
                      newSet.add(expandedChunk.chunk_id);
                      setSelectedChunkIds(newSet);
                    }
                  }
                }}
                className="w-full h-[50vh] p-5 font-semibold text-sm leading-relaxed border border-slate-200/50 dark:border-slate-700 rounded-2xl bg-slate-50 text-slate-800 dark:bg-[#100220] dark:text-slate-200 focus:outline-none focus:border-tuh-rose transition resize-none custom-scrollbar"
                placeholder="พิมพ์แก้ไขเนื้อหาของ Chunk นี้ในขนาดที่ใหญ่ขึ้น..."
              />
              <div className="text-xs text-slate-500 dark:text-slate-400 font-bold">
                📏 ความยาวปัจจุบัน: {expandedChunk.content?.length || 0} ตัวอักษร
              </div>
            </div>

            <div className="p-6 border-t border-slate-100 dark:border-tuh-purple/20 flex justify-end gap-3 bg-slate-50/50 dark:bg-tuh-navy/20">
              <button
                type="button"
                onClick={() => setExpandedChunk(null)}
                className="px-5 py-2.5 rounded-2xl text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 font-semibold transition active:scale-95"
              >
                ย้อนกลับ
              </button>
              <button
                type="button"
                disabled={savingContent}
                onClick={() => {
                  handleSaveIndividualChunk(previewFilename, expandedChunk.chunk_id, expandedChunk.content);
                  setExpandedChunk(null);
                }}
                className="bg-tuh-gradient-2 text-white font-bold py-2.5 px-6 rounded-2xl hover:shadow-lg transition active:scale-[0.98] flex items-center gap-1.5"
              >
                {savingContent ? (
                  <i className="fa-solid fa-spinner animate-spin"></i>
                ) : (
                  <i className="fa-solid fa-check"></i>
                )}
                ยืนยันและบันทึกด่วน
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: EDIT PREDEFINED FAQ MODAL */}
      {showEditPredefinedFaqModal && selectedPredefinedFaq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-[#2c0548]/95 rounded-3xl border border-slate-200 dark:border-tuh-purple/35 shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6 border-b border-slate-100 dark:border-tuh-purple/20 flex justify-between items-center bg-slate-50 dark:bg-tuh-navy/55">
              <h3 className="font-extrabold text-lg text-tuh-navy dark:text-white flex items-center gap-2">
                <i className="fa-solid fa-pen-to-square text-tuh-rose"></i> แก้ไขคำถามที่พบบ่อย (ปุ่มหน้าแรก)
              </h3>
              <button
                onClick={() => { setShowEditPredefinedFaqModal(false); setSelectedPredefinedFaq(null); }}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-500 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition"
              >
                <i className="fa-solid fa-xmark text-lg"></i>
              </button>
            </div>

            <form onSubmit={handleSavePredefinedFaq} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">หัวข้อคำถาม (ปุ่ม)</label>
                <input
                  type="text"
                  required
                  placeholder="พิมพ์ประโยคคำถาม..."
                  value={predefinedFaqQuestion}
                  onChange={(e) => setPredefinedFaqQuestion(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  คลาสไอคอน FontAwesome (เช่น fa-circle-question, fa-eye, fa-hospital)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-tuh-rose flex items-center justify-center">
                    <i className={`fa-solid ${predefinedFaqIcon || 'fa-circle-question'}`}></i>
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="ใส่คลาสไอคอน FontAwesome..."
                    value={predefinedFaqIcon}
                    onChange={(e) => setPredefinedFaqIcon(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 pl-10 pr-4 focus:outline-none focus:border-tuh-rose transition font-semibold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  คำตอบของคำถามนี้ (หากต้องการระบุคำตอบตายตัว)
                </label>
                <textarea
                  placeholder="พิมพ์ข้อความคำตอบของปุ่มนี้หากต้องการคำตอบที่แน่นอน... (หรือเว้นว่างไว้เพื่อให้ AI ค้นหาจาก PDF)"
                  value={predefinedFaqAnswer}
                  onChange={(e) => setPredefinedFaqAnswer(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-50 dark:bg-[#100220]/45 border border-slate-200 dark:border-tuh-purple/20 rounded-2xl py-3 px-4 focus:outline-none focus:border-tuh-rose transition font-semibold text-sm whitespace-pre-wrap leading-relaxed"
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
