/**
 * TUH Chatbot AI — AdminWeb Application Root Component
 * โครงสร้างสถาปัตยกรรมระดับ Front-end:
 * 1. รวม Custom Hooks ทั้ง 12 ตัวเพื่อแยก Business Logic ออกจาก UI อย่างเด็ดขาด
 * 2. ใช้ React Context (AdminContext) ในการกระจาย State และ Action Handlers ให้ทุกหน้า (Page)
 * 3. ควบคุม Tab Routing ด้วย activeTab-string ร่วมกับ localStorage
 * 4. ครอบด้วย AdminShell Layout สำหรับหน้าจอหลัง Login
 */
import React, { useState, useEffect } from 'react';
import { AdminContext } from './context/AdminContext';
import AdminShell from './layouts/AdminShell';
import LoginPage from './pages/LoginPage';
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
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';
import { useProfile } from './hooks/useProfile';
import { useDashboardData } from './hooks/useDashboardData';
import { useSettingsState } from './hooks/useSettingsState';
import { useDocumentsState } from './hooks/useDocumentsState';
import { useFormsState } from './hooks/useFormsState';
import { useAnnouncementsState } from './hooks/useAnnouncementsState';
import { useUsersState } from './hooks/useUsersState';
import { useFeedbackAndUnansweredState } from './hooks/useFeedbackAndUnansweredState';
import { useHistoryState } from './hooks/useHistoryState';
import { useDeleteConfirmation } from './hooks/useDeleteConfirmation';

// กำหนด URL ของ Backend API (อ่านจาก .env หรือ fallback เป็น host ปัจจุบันที่พอร์ต 8000)
const API_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

function App() {
  // จัดการ State การสลับแท็บเมนูหลัก (เก็บลง localStorage เพื่อคงหน้าเดิมเมื่อรีเฟรช)
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

  // Alert Banner States (trivial — ใช้ร่วมกันแทบทุกโดเมน จึงส่งเป็นพารามิเตอร์เข้า hook อื่นๆ)
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };
  const showError = (msg) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(''), 4000);
  };

  const { isDarkMode, setIsDarkMode } = useTheme();

  const {
    fetch,
    isLoggedIn,
    username,
    setUsername,
    password,
    setPassword,
    loginError,
    loginLoading,
    adminUser,
    showPassword,
    setShowPassword,
    handleLogin,
    handleLogout,
  } = useAuth(API_URL, showSuccess, showError, setActiveTab);

  const {
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,
    showNewPassword,
    setShowNewPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    handleUpdatePassword,
  } = useProfile(API_URL, fetch, showSuccess, showError);

  const { stats, fetchStats, trendDrawer, setTrendDrawer } = useDashboardData(API_URL, fetch);

  const { settings, setSettings, fetchSettings, handleSaveSettings } = useSettingsState(API_URL, fetch, showSuccess, showError);

  const {
    documents,
    dragOver,
    uploading,
    uploadProgress,
    showEditDocModal,
    setShowEditDocModal,
    selectedDoc,
    setSelectedDoc,
    editDisplayName,
    setEditDisplayName,
    selectedFileForUpload,
    setSelectedFileForUpload,
    preExcludePages,
    setPreExcludePages,
    preDisplayName,
    setPreDisplayName,
    showPreUploadModal,
    setShowPreUploadModal,
    previewContent,
    setPreviewContent,
    previewChunks,
    setPreviewChunks,
    previewFilename,
    setPreviewFilename,
    previewModalType,
    setPreviewModalType,
    approvingFilename,
    loadingPreview,
    savingContent,
    selectedChunkIds,
    setSelectedChunkIds,
    expandedChunk,
    setExpandedChunk,
    docSearchQuery,
    setDocSearchQuery,
    docSortField,
    docSortOrder,
    docCurrentPage,
    setDocCurrentPage,
    fetchDocuments,
    handleSort,
    handleApproveStep,
    handleViewPreview,
    handleSaveContent,
    handleSaveIndividualChunk,
    handleSaveSelectedChunks,
    handleSaveAllChunks,
    handleToggleDocStatus,
    handleOpenEditDocModal,
    handleSaveDocDetails,
    uploadFile,
    handleDrop,
    handleDragOver,
    handleDragLeave,
  } = useDocumentsState(API_URL, fetch, showSuccess, showError, fetchStats);

  const {
    forms,
    formName,
    setFormName,
    setFormFile,
    formPage,
    setFormPage,
    formSearchQuery,
    setFormSearchQuery,
    fetchForms,
    handleAddForm,
  } = useFormsState(API_URL, fetch, showSuccess, showError);

  // Delete Confirmation Modal State (trivial — ไม่มี effect ของตัวเอง แต่ใช้ร่วมกันทั้ง
  // useAnnouncementsState (handleDeleteAnnouncement ต้องปิด modal เอง) และ useDeleteConfirmation
  // (confirmDelete dispatcher) จึงต้องประกาศไว้ก่อนเรียก hook ทั้งสอง เพื่อเลี่ยง circular dependency)
  const [deleteModalState, setDeleteModalState] = useState({ show: false, type: null, targetId: null, targetName: null });

  const {
    announcements,
    annTitle,
    setAnnTitle,
    annContent,
    setAnnContent,
    annStartDate,
    setAnnStartDate,
    annEndDate,
    setAnnEndDate,
    annFilter,
    setAnnFilter,
    editingAnnId,
    setEditingAnnId,
    isAnnFormOpen,
    setIsAnnFormOpen,
    annPinned,
    setAnnPinned,
    annCategory,
    setAnnCategory,
    fetchAnnouncements,
    handleCreateAnnouncement,
    handleEditAnnouncement,
    handleCancelEditAnnouncement,
    handleDeleteAnnouncement,
  } = useAnnouncementsState(API_URL, fetch, showSuccess, showError, setDeleteModalState);

  const {
    users,
    loadingUsers,
    showUserModal,
    setShowUserModal,
    userFormMode,
    setUserFormMode,
    selectedUser,
    setSelectedUser,
    userFormUsername,
    setUserFormUsername,
    userFormPassword,
    setUserFormPassword,
    userFormDisplayName,
    setUserFormDisplayName,
    userFormRole,
    setUserFormRole,
    userFormIsActive,
    setUserFormIsActive,
    userFormDepartment,
    setUserFormDepartment,
    departments,
    fetchUsers,
    handleCreateOrUpdateUser,
  } = useUsersState(API_URL, fetch, showSuccess, showError);

  const {
    feedback,
    unanswered,
    showFaqModal,
    setShowFaqModal,
    currentUnanswered,
    setCurrentUnanswered,
    faqAnswer,
    setFaqAnswer,
    analysisLoading,
    analysisResult,
    showEditPredefinedFaqModal,
    setShowEditPredefinedFaqModal,
    selectedPredefinedFaq,
    setSelectedPredefinedFaq,
    predefinedFaqQuestion,
    setPredefinedFaqQuestion,
    predefinedFaqAnswer,
    setPredefinedFaqAnswer,
    predefinedFaqIcon,
    setPredefinedFaqIcon,
    unansweredSortOrder,
    setUnansweredSortOrder,
    unansweredStartDate,
    setUnansweredStartDate,
    unansweredEndDate,
    setUnansweredEndDate,
    pendingUnansweredCount,
    fetchFeedback,
    fetchUnanswered,
    handleResolveUnanswered,
    handleSubmitFaq,
    handleOpenEditPredefinedFaqModal,
    handleSavePredefinedFaq,
  } = useFeedbackAndUnansweredState(API_URL, fetch, showSuccess, showError, settings, setSettings, fetchStats);

  const {
    history,
    chunksMap,
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
  } = useHistoryState(API_URL, fetch, feedback);

  const { confirmDelete } = useDeleteConfirmation({
    API_URL,
    fetch,
    showSuccess,
    showError,
    deleteModalState,
    setDeleteModalState,
    fetchDocuments,
    fetchStats,
    fetchForms,
    fetchUsers,
    handleDeleteAnnouncement,
  });

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  // Refetch history when switching to history tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'history') {
      fetchHistory();
      fetchHistoryChunksMap();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isLoggedIn]);

  // Refetch announcements when switching to announcements tab
  useEffect(() => {
    if (isLoggedIn && activeTab === 'announcements') {
      fetchAnnouncements();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isLoggedIn]);

  // Refetch users when switching to users tab and is System Administrator
  useEffect(() => {
    if (isLoggedIn && activeTab === 'users' && adminUser.role === 'System Administrator') {
      fetchUsers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isLoggedIn, adminUser.role]);

  // Safety redirect: If a non-System Administrator lands on users or settings tab, redirect them to dashboard
  useEffect(() => {
    if (isLoggedIn && adminUser) {
      if (adminUser.role !== 'System Administrator' && (activeTab === 'users' || activeTab === 'settings')) {
        setActiveTab('dashboard');
      }
    }
  }, [isLoggedIn, activeTab, adminUser.role]);

  // Login View
  if (!isLoggedIn) {
    return (
      <LoginPage
        successMsg={successMsg}
        errorMsg={errorMsg}
        loginError={loginError}
        loginLoading={loginLoading}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        showPassword={showPassword}
        setShowPassword={setShowPassword}
        handleLogin={handleLogin}
      />
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
