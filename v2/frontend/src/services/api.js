/**
 * TUH Chatbot AI v2 — API Service Layer
 * Senior Frontend Developer: axios interceptors + JWT auto-refresh
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// ─── Request Interceptor: Auto-attach Authorization header ───────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tuh_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response Interceptor: Auto-refresh token on 401 ────────────────────────
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('tuh_refresh_token');
      if (!refreshToken) {
        isRefreshing = false;
        localStorage.clear();
        window.location.href = '/admin/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem('tuh_access_token', data.access_token);
        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
        processQueue(null, data.access_token);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.clear();
        window.location.href = '/admin/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── API Methods ─────────────────────────────────────────────────────────────

export const chatAPI = {
  sendMessage: (query, history, sessionId) =>
    api.post('/api/chat', { query, history, session_id: sessionId }),
  getPublicSettings: () => api.get('/api/chat/settings'),
};

export const authAPI = {
  login: (username, password) =>
    api.post('/api/auth/login', { username, password }),
  refresh: (refreshToken) =>
    api.post('/api/auth/refresh', { refresh_token: refreshToken }),
  getMe: () => api.get('/api/auth/me'),
  listUsers: () => api.get('/api/auth/users'),
  createUser: (data) => api.post('/api/auth/users', data),
  updateUser: (id, data) => api.put(`/api/auth/users/${id}`, data),
  deleteUser: (id) => api.delete(`/api/auth/users/${id}`),
};

export const adminAPI = {
  // Documents
  getDocuments: () => api.get('/api/admin/documents'),
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/admin/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  updateDocument: (filename, data) => api.put(`/api/admin/documents/${encodeURIComponent(filename)}`, data),
  deleteDocument: (filename) => api.delete(`/api/admin/documents/${encodeURIComponent(filename)}`),

  // Settings
  getSettings: () => api.get('/api/admin/settings'),
  updateSettings: (data) => api.put('/api/admin/settings', data),

  // Feedback
  getFeedback: () => api.get('/api/admin/feedback'),
  deleteFeedback: (id) => api.delete(`/api/admin/feedback/${id}`),

  // Unanswered
  getUnanswered: () => api.get('/api/admin/unanswered'),
  updateUnanswered: (id, data) => api.put(`/api/admin/unanswered/${id}`, data),
  deleteUnanswered: (id) => api.delete(`/api/admin/unanswered/${id}`),

  // Stats
  getStats: () => api.get('/api/admin/stats'),

  // Rebuild
  triggerRebuild: () => api.post('/api/admin/rebuild'),
  getRebuildStatus: () => api.get('/api/admin/rebuild/status'),

  // Forms
  getForms: () => api.get('/api/admin/forms'),
  createForm: (data) => api.post('/api/admin/forms', data),
  deleteForm: (id) => api.delete(`/api/admin/forms/${id}`),

  // Announcements
  getAnnouncements: () => api.get('/api/admin/announcements'),
  createAnnouncement: (data) => api.post('/api/admin/announcements', data),
  updateAnnouncement: (id, data) => api.put(`/api/admin/announcements/${id}`, data),
  deleteAnnouncement: (id) => api.delete(`/api/admin/announcements/${id}`),

  // History
  getHistory: (limit = 100) => api.get(`/api/admin/history?limit=${limit}`),

  // Feedback submit (public)
  submitFeedback: (data) => api.post('/api/admin/feedback/submit', data),
  submitUnanswered: (query) => api.post('/api/admin/unanswered/submit', { query }),
};

export default api;
