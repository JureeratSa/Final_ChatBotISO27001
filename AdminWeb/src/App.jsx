import React, { useState, useEffect } from 'react';
import { AdminContext } from './context/AdminContext';
import AdminShell from './layouts/AdminShell';
import DashboardPage from './pages/DashboardPage';
import SatisfactionPage from './pages/SatisfactionPage';
import DocumentsPage from './pages/DocumentsPage';
import AnnouncementsPage from './pages/AnnouncementsPage';
import LogsPage from './pages/LogsPage';
import HistoryPage from './pages/HistoryPage';
import FaqsPage from './pages/FaqsPage';
import SettingsPage from './pages/SettingsPage';
import ProfilePage from './pages/ProfilePage';
import UsersPage from './pages/UsersPage';

// เดิม hardcode เป็น http://<hostname>:8000 ตรงๆ ทำให้พังทันทีถ้า deploy หลัง HTTPS/reverse
// proxy (mixed content ถูก browser บล็อก) — อ่านจาก VITE_API_URL ก่อน ถ้าไม่ตั้งค่าไว้ค่อย
// fallback เป็นพฤติกรรมเดิมสำหรับ local dev
const API_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

function App() {
  let logoutRef = () => { };

  const fetch = (url, options = {}) => {
    const urlStr = typeof url === 'string' ? url : (url.url || '');
    const isLogin = urlStr.includes('/api/admin/login') || urlStr.includes('/api/auth/login');
    const isFeedbackOrUnansweredSubmit = urlStr.includes('/api/admin/feedback/submit') || urlStr.includes('/api/admin/unanswered/submit');
    const isAdmin = urlStr.includes('/api/admin/') || urlStr.includes('/api/auth/');

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
    embedding_tech: 'local_chroma'
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
  const [editDisplayName, setEditDisplayName] = useState('');

  // Pre-upload document options
  const [selectedFileForUpload, setSelectedFileForUpload] = useState(null);
  const [preExcludePages, setPreExcludePages] = useState('');
  const [preDisplayName, setPreDisplayName] = useState('');
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
  const [docCurrentPage, setDocCurrentPage] = useState(1);

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
  const [isAnnFormOpen, setIsAnnFormOpen] = useState(false);
  const [annPinned, setAnnPinned] = useState(false);
  const [annCategory, setAnnCategory] = useState('');

  // User Management States
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [showUserModal, setShowUserModal] = useState(false);
  const [userFormMode, setUserFormMode] = useState('create'); // 'create' | 'edit'
  const [selectedUser, setSelectedUser] = useState(null);
  const [userFormUsername, setUserFormUsername] = useState('');
  const [userFormPassword, setUserFormPassword] = useState('');
  const [userFormDisplayName, setUserFormDisplayName] = useState('');
  const [userFormRole, setUserFormRole] = useState('admin');
  const [userFormIsActive, setUserFormIsActive] = useState(true);
  const [userFormDepartment, setUserFormDepartment] = useState('');

  // Bot Response History States
  const [history, setHistory] = useState([]);
  const [chunksMap, setChunksMap] = useState({});
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [satPeriod, setSatPeriod] = useState('weekly');
  const [historyPeriod, setHistoryPeriod] = useState('weekly');
  // Slide-out panel showing the Q&A behind a clicked point on the dashboard trend chart
  const [trendDrawer, setTrendDrawer] = useState(null); // { dateLabel, type: 'answered' | 'unanswered', items: [] }
  const departments = Array.from(new Set(users.map(u => u.department).filter(Boolean)));

  // Sort and Date Filter States for History
  const [historySortOrder, setHistorySortOrder] = useState('desc'); // 'desc' = newest first, 'asc' = oldest first
  const [historyStartDate, setHistoryStartDate] = useState('');
  const [historyEndDate, setHistoryEndDate] = useState('');
  const [historyLimit, setHistoryLimit] = useState(() => {
    return localStorage.getItem('tuh_admin_history_limit') || '1000';
  });

  // Sort and Date Filter States for Unanswered Logs
  const [unansweredSortOrder, setUnansweredSortOrder] = useState('desc'); // 'desc' = newest first, 'asc' = oldest first
  const [unansweredStartDate, setUnansweredStartDate] = useState('');
  const [unansweredEndDate, setUnansweredEndDate] = useState('');

  // Password Visibility Toggle States
  const [showPassword, setShowPassword] = useState(false);
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

  // Persist History Limit Preference
  useEffect(() => {
    localStorage.setItem('tuh_admin_history_limit', historyLimit);
  }, [historyLimit]);

  // Fetch data on login
  useEffect(() => {
    if (isLoggedIn) {
      fetchStats();
      fetchDocuments();
      fetchFeedback();
      fetchUnanswered();
      fetchSettings();
      fetchHistory();
      // ดึง chunksMap ตั้งแต่ตอน login เลย (ไม่ใช่รอสลับไปแท็บ history) เพื่อให้
      // badge #chunk_id ในหน้าภาพรวม (Dashboard trend drawer) กดเปิด PDF ได้ทันที
      fetchHistoryChunksMap();
      fetchForms();
      fetchAnnouncements();
      if (adminUser.role === 'System Administrator') {
        fetchUsers();
      }
    }
  }, [isLoggedIn]);

  // Refetch history when switching to history tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'history') {
      fetchHistory();
      fetchHistoryChunksMap();
    }
  }, [activeTab, isLoggedIn]);

  // Refetch announcements when switching to announcements tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'announcements') {
      fetchAnnouncements();
    }
  }, [activeTab, isLoggedIn]);

  // Refetch users when switching to users tab and is System Administrator
  useEffect(() => {
    if (isLoggedIn && activeTab === 'users' && adminUser.role === 'System Administrator') {
      fetchUsers();
    }
  }, [activeTab, isLoggedIn, adminUser.role]);

  // Reset document page when search query or sort field/order changes
  useEffect(() => {
    setDocCurrentPage(1);
  }, [docSearchQuery, docSortField, docSortOrder]);

  // Safety redirect: If a non-System Administrator lands on users or settings tab, redirect them to dashboard
  useEffect(() => {
    if (isLoggedIn && adminUser) {
      if (adminUser.role !== 'System Administrator' && (activeTab === 'users' || activeTab === 'settings')) {
        setActiveTab('dashboard');
      }
    }
  }, [isLoggedIn, activeTab, adminUser.role]);

  // Alert Banner Helpers
  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };
  const showError = (msg) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(''), 4000);
  };

  // API Call Helpers หน้าภาพรวม
  const fetchStats = () => {
    fetch(API_URL + '/api/admin/stats')
      .then(r => r.json())
      .then(data => {
        setStats({
          total_queries: data.total_queries || 0,
          likes: data.total_likes || 0,
          dislikes: data.total_dislikes || 0,
          pending_unanswered: data.total_unanswered || 0,
          total_documents: data.total_documents || 0,
          active_documents: data.active_documents || 0,
          queries_today: data.queries_today || 0,
          avg_response_time: data.avg_response_time || 0.0
        });
      })
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
    } else if (deleteModalState.type === 'announcement') {
      handleDeleteAnnouncement(deleteModalState.targetId);
    } else if (deleteModalState.type === 'user') {
      fetch(API_URL + `/api/auth/users/${deleteModalState.targetId}`, {
        method: 'DELETE'
      })
        .then(res => {
          if (res.status === 204 || res.ok) {
            showSuccess("ลบบัญชีแอดมินเรียบร้อยแล้ว");
            fetchUsers();
          } else {
            return res.json().then(data => {
              throw new Error(data.detail || "ไม่สามารถลบผู้ใช้นี้ได้");
            });
          }
        })
        .catch(err => showError(err.message || "เกิดข้อผิดพลาดในการลบบัญชี"))
        .finally(() => {
          setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
        });
    }
  };

  const fetchUsers = () => {
    setLoadingUsers(true);
    fetch(API_URL + '/api/auth/users')
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถโหลดข้อมูลบัญชีผู้ใช้ได้");
        return res.json();
      })
      .then(data => setUsers(data))
      .catch(err => console.error("Error fetching users:", err))
      .finally(() => setLoadingUsers(false));
  };

  const handleCreateOrUpdateUser = (e) => {
    e.preventDefault();
    if (!userFormUsername.trim() || !userFormDisplayName.trim()) {
      showError("กรุณากรอกข้อมูล Username และ ชื่อแสดงผล");
      return;
    }

    if (userFormMode === 'create' && !userFormPassword.trim()) {
      showError("กรุณากรอกรหัสผ่านสำหรับผู้ใช้ใหม่");
      return;
    }

    const url = userFormMode === 'create'
      ? API_URL + '/api/auth/users'
      : API_URL + `/api/auth/users/${selectedUser.id}`;
    const method = userFormMode === 'create' ? 'POST' : 'PUT';

    const payload = {
      username: userFormUsername,
      display_name: userFormDisplayName,
      role: userFormRole,
      department: userFormDepartment,
      is_active: userFormIsActive
    };

    if (userFormPassword.trim()) {
      payload.password = userFormPassword;
    }

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            throw new Error(data.detail || "บันทึกข้อมูลไม่สำเร็จ");
          });
        }
        return res.json();
      })
      .then(() => {
        showSuccess(userFormMode === 'create' ? "สร้างบัญชีแอดมินใหม่สำเร็จ" : "แก้ไขบัญชีแอดมินสำเร็จ");
        setShowUserModal(false);
        fetchUsers();
      })
      .catch(err => showError(err.message || "เกิดข้อผิดพลาดในการบันทึกข้อมูล"));
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
      end_date: annEndDate,
      category: annCategory,
      pinned: annPinned
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
          setAnnCategory('');
          setEditingAnnId(null);
          setAnnPinned(false);
          setIsAnnFormOpen(false);
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
    setAnnPinned(ann.pinned || false);
    setAnnCategory(ann.category || '');
    setIsAnnFormOpen(true);
  };

  const handleCancelEditAnnouncement = () => {
    setAnnTitle('');
    setAnnContent('');
    setAnnStartDate('');
    setAnnEndDate('');
    setAnnCategory('');
    setEditingAnnId(null);
    setAnnPinned(false);
    setIsAnnFormOpen(false);
  };

  const handleDeleteAnnouncement = (annId) => {
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
      .catch(err => showError("เกิดข้อผิดพลาดในการลบประกาศ"))
      .finally(() => {
        setDeleteModalState({ show: false, type: null, targetId: null, targetName: null });
      });
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
    fetch(API_URL + '/api/admin/history')
      .then(r => r.json())
      .then(data => {
        const sortedData = (data || []).reverse();
        setHistory(sortedData);
      })
      .catch(err => console.error("Error fetching history:", err))
      .finally(() => setLoadingHistory(false));
  };

  // นับเฉพาะคำถามที่ยังไม่ได้ตรวจเช็ค (status ตรวจเช็คเรียบร้อยแล้วไม่ต้องนับ)
  const pendingUnansweredCount = unanswered.filter(u => u.status === 'Pending').length;

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
    setUsername('');
    setPassword('');
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
    fetch(API_URL + '/api/admin/unanswered/' + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
      .then(r => {
        if (!r.ok) throw new Error('update failed');
        return r.json();
      })
      .then(() => {
        showSuccess("อัปเดตสถานะล็อกคำถามเรียบร้อยแล้ว");
        fetchUnanswered();
        fetchStats();
      })
      .catch(err => {
        console.error(err);
        showError("ไม่สามารถอัปเดตสถานะได้");
      });
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

  const handleOpenEditDocModal = (doc) => {
    setSelectedDoc(doc);
    setEditDisplayName(doc.display_name || doc.filename);
    setShowEditDocModal(true);

    if (doc.status === 'Active' || doc.status === 'Step_Chunk_Preview') {
      setLoadingPreview(true);
      setPreviewChunks([]);
      setOriginalChunks([]);
      setSelectedChunkIds(new Set());

      fetch(API_URL + `/api/admin/documents/view_chunks?filename=${encodeURIComponent(doc.filename)}`)
        .then(res => {
          if (!res.ok) throw new Error("ไม่สามารถดึงข้อมูลพรีวิวได้");
          return res.json();
        })
        .then(data => {
          const loadedChunks = data.chunks || [];
          setPreviewChunks(loadedChunks);
          setOriginalChunks(JSON.parse(JSON.stringify(loadedChunks)));
          setLoadingPreview(false);
        })
        .catch(err => {
          console.error("Error fetching chunks:", err);
          setLoadingPreview(false);
        });
    } else {
      setPreviewChunks([]);
      setOriginalChunks([]);
    }
  };

  const handleSaveDocDetails = (e) => {
    e.preventDefault();
    if (!selectedDoc) return;

    fetch(API_URL + '/api/admin/documents/update_details', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        filename: selectedDoc.filename,
        display_name: editDisplayName
      })
    })
      .then(res => {
        if (!res.ok) throw new Error("ไม่สามารถบันทึกชื่อแสดงผลได้");
        return res.json();
      })
      .then(() => {
        showSuccess("บันทึกข้อมูลเอกสารเรียบร้อยแล้ว!");
        fetchDocuments();
        setShowEditDocModal(false);
        setSelectedDoc(null);
      })
      .catch(err => {
        showError(`เกิดข้อผิดพลาด: ${err.message}`);
      });
  };

  // PDF File Upload Handler
  const uploadFile = (file, excludePagesText = '', displayNameText = '') => {
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
          'X-Exclude-Pages': excludePagesText,
          'X-Display-Name': encodeURIComponent(displayNameText || file.name)
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
      const file = e.dataTransfer.files[0];
      setSelectedFileForUpload(file);
      setPreExcludePages('');
      setPreDisplayName(file.name);
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


  // Dashboard Main View — ประกอบ layout (AdminShell) + แชร์ state/handler ทั้งหมดผ่าน
  // AdminContext ให้ page component ของแต่ละแท็บดึงไปใช้เอง (ไม่ prop-drilling)
  const contextValue = {
    API_URL,
    activeTab,
    adminUser,
    analysisLoading,
    analysisResult,
    annCategory,
    annContent,
    annEndDate,
    annFilter,
    annPinned,
    annStartDate,
    annTitle,
    announcements,
    approvingFilename,
    chunksMap,
    confirmDelete,
    confirmPassword,
    currentUnanswered,
    departments,
    deleteModalState,
    docCurrentPage,
    docSearchQuery,
    docSortField,
    docSortOrder,
    documents,
    downloadCSV,
    dragOver,
    editDisplayName,
    editingAnnId,
    errorMsg,
    expandedChunk,
    faqAnswer,
    feedback,
    filteredHistory,
    formName,
    formPage,
    formSearchQuery,
    forms,
    getSatisfactionStatsByPeriod,
    handleAddForm,
    handleApproveStep,
    handleCancelEditAnnouncement,
    handleCreateAnnouncement,
    handleCreateOrUpdateUser,
    handleDragLeave,
    handleDragOver,
    handleDrop,
    handleEditAnnouncement,
    handleLogout,
    handleOpenEditDocModal,
    handleOpenEditPredefinedFaqModal,
    handleResolveUnanswered,
    handleSaveAllChunks,
    handleSaveContent,
    handleSaveDocDetails,
    handleSaveIndividualChunk,
    handleSaveSelectedChunks,
    handleSavePredefinedFaq,
    handleSaveSettings,
    handleSort,
    handleSubmitFaq,
    handleTabClick,
    handleToggleDocStatus,
    handleUpdatePassword,
    handleViewPreview,
    history,
    historyEndDate,
    historyLimit,
    historyPeriod,
    historySortOrder,
    historyStartDate,
    isAnnFormOpen,
    isDarkMode,
    isSidebarOpen,
    loadingHistory,
    loadingPreview,
    loadingUsers,
    newPassword,
    parseTimestamp,
    pendingUnansweredCount,
    preDisplayName,
    preExcludePages,
    predefinedFaqAnswer,
    predefinedFaqIcon,
    predefinedFaqQuestion,
    previewChunks,
    previewContent,
    previewFilename,
    previewModalType,
    satPeriod,
    savingContent,
    selectedChunkIds,
    selectedDoc,
    selectedFileForUpload,
    selectedPredefinedFaq,
    selectedUser,
    setActiveTab,
    setAnnCategory,
    setAnnContent,
    setAnnEndDate,
    setAnnFilter,
    setAnnPinned,
    setAnnStartDate,
    setAnnTitle,
    setConfirmPassword,
    setCurrentUnanswered,
    setDeleteModalState,
    setDocCurrentPage,
    setDocSearchQuery,
    setEditDisplayName,
    setEditingAnnId,
    setExpandedChunk,
    setFaqAnswer,
    setFormFile,
    setFormName,
    setFormPage,
    setFormSearchQuery,
    setHistoryEndDate,
    setHistoryLimit,
    setHistoryPeriod,
    setHistorySortOrder,
    setHistoryStartDate,
    setIsAnnFormOpen,
    setIsDarkMode,
    setIsSidebarOpen,
    setNewPassword,
    setPreDisplayName,
    setPreExcludePages,
    setPredefinedFaqAnswer,
    setPredefinedFaqIcon,
    setPredefinedFaqQuestion,
    setPreviewChunks,
    setPreviewContent,
    setPreviewFilename,
    setPreviewModalType,
    setSatPeriod,
    setSelectedChunkIds,
    setSelectedDoc,
    setSelectedFileForUpload,
    setSelectedPredefinedFaq,
    setSelectedUser,
    setSettings,
    setShowConfirmPassword,
    setShowEditDocModal,
    setShowEditPredefinedFaqModal,
    setShowFaqModal,
    setShowNewPassword,
    setShowPreUploadModal,
    setShowUserModal,
    setTrendDrawer,
    setUnansweredEndDate,
    setUnansweredSortOrder,
    setUnansweredStartDate,
    setUserFormDepartment,
    setUserFormDisplayName,
    setUserFormIsActive,
    setUserFormMode,
    setUserFormPassword,
    setUserFormRole,
    setUserFormUsername,
    settings,
    showConfirmPassword,
    showEditDocModal,
    showEditPredefinedFaqModal,
    showFaqModal,
    showNewPassword,
    showPreUploadModal,
    showSuccess,
    showUserModal,
    stats,
    successMsg,
    trendDrawer,
    unanswered,
    unansweredEndDate,
    unansweredSortOrder,
    unansweredStartDate,
    uploadFile,
    uploadProgress,
    uploading,
    userFormDepartment,
    userFormDisplayName,
    userFormIsActive,
    userFormMode,
    userFormPassword,
    userFormRole,
    userFormUsername,
    users,
  };

  return (
    <AdminContext.Provider value={contextValue}>
      <AdminShell>
        {activeTab === 'dashboard' && <DashboardPage />}
        {activeTab === 'satisfaction' && <SatisfactionPage />}
        {activeTab === 'documents' && <DocumentsPage />}
        {activeTab === 'announcements' && <AnnouncementsPage />}
        {activeTab === 'logs' && <LogsPage />}
        {activeTab === 'history' && <HistoryPage />}
        {activeTab === 'faqs' && <FaqsPage />}
        {activeTab === 'settings' && adminUser.role === 'System Administrator' && <SettingsPage />}
        {activeTab === 'profile' && <ProfilePage />}
        {activeTab === 'users' && adminUser.role === 'System Administrator' && <UsersPage />}
      </AdminShell>
    </AdminContext.Provider>
  );
}

export default App;
