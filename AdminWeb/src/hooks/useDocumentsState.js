import { useState, useEffect } from 'react';

/**
 * useDocumentsState — โดเมนที่ใหญ่ที่สุดของ AdminWeb: รายการเอกสาร PDF, การอัปโหลด,
 * pipeline อนุมัติ (raw → clean → chunk → active), พรีวิว/แก้ไขเนื้อหาแต่ละขั้นตอน,
 * แก้ไขรายละเอียดเอกสารและ chunk ทั้งหมด รวมถึงตาราง/ค้นหา/แบ่งหน้า
 * แยกออกมาจาก App.jsx เดิมแบบ verbatim ไม่เปลี่ยนพฤติกรรม
 */
export function useDocumentsState(API_URL, fetch, showSuccess, showError, fetchStats) {
  const [documents, setDocuments] = useState([]);

  // UI States (upload)
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

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

  // Reset document page when search query or sort field/order changes
  useEffect(() => {
    setDocCurrentPage(1);
  }, [docSearchQuery, docSortField, docSortOrder]);

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

  // PDF File Upload Handler — คืน Promise<boolean> (หน้า Logs ใช้รู้ว่าอัปโหลดสำเร็จก่อนปิดรายการคำถาม)
  const uploadFile = (file, excludePagesText = '', displayNameText = '') => new Promise((resolve) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showError("ระบบสนับสนุนการอัปโหลดไฟล์นามสกุล .pdf เท่านั้น");
      resolve(false);
      return;
    }

    setUploading(true);
    setUploadProgress(10);

    const reader = new FileReader();
    reader.readAsArrayBuffer(file);
    reader.onerror = () => {
      showError("ไม่สามารถอ่านไฟล์ที่เลือกได้");
      setUploading(false);
      setUploadProgress(0);
      resolve(false);
    };
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
          resolve(true);
        })
        .catch(err => {
          showError(`เกิดข้อผิดพลาดในการอัปโหลด: ${err.message}`);
          setUploading(false);
          setUploadProgress(0);
          resolve(false);
        });
    };
  });

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

  return {
    documents,
    setDocuments,
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
    originalChunks,
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
  };
}
