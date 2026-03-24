import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('aikosh5-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('aikosh5-token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const pdaApi = {
  detect: (data: { imagery_id?: number; bbox?: number[]; detection_types?: string[]; confidence_threshold?: number }) =>
    api.post('/pda/detect', data),

  getStatus: (taskId: string) =>
    api.get(`/pda/status/${taskId}`),

  getTasks: (params?: { status?: string; limit?: number }) =>
    api.get('/pda/tasks', { params }),

  getDetections: (params?: {
    bbox?: string;
    detection_type?: string;
    min_confidence?: number;
    imagery_id?: number;
    limit?: number;
    offset?: number;
  }) =>
    api.get('/pda/detections', { params }),

  getDetection: (id: number) =>
    api.get(`/pda/detections/${id}`),

  verifyDetection: (id: number, verifiedBy: string) =>
    api.post(`/pda/detections/${id}/verify`, null, { params: { verified_by: verifiedBy } }),

  matchDetections: (detectionIds: number[], autoCreate?: boolean) =>
    api.post('/pda/match', detectionIds, { params: { auto_create: autoCreate } }),

  getImagery: (params?: {
    bbox?: string;
    start_date?: string;
    end_date?: string;
    satellite?: string;
    limit?: number;
  }) =>
    api.get('/pda/imagery', { params }),

  getStatistics: (params?: { imagery_id?: number; detection_type?: string; days?: number }) =>
    api.get('/pda/statistics', { params }),
}

export const cdaApi = {
  compare: (data: {
    imagery_before_id: number;
    imagery_after_id: number;
    bbox?: number[];
    change_types?: string[];
    confidence_threshold?: number;
  }) => api.post('/cda/compare', data),

  getStatus: (taskId: string) =>
    api.get(`/cda/status/${taskId}`),

  getTasks: (params?: { status?: string; limit?: number }) =>
    api.get('/cda/tasks', { params }),

  getChanges: (params?: {
    bbox?: string;
    change_type?: string;
    severity?: string;
    start_date?: string;
    end_date?: string;
    min_confidence?: number;
    is_verified?: boolean;
    limit?: number;
    offset?: number;
  }) =>
    api.get('/cda/changes', { params }),

  getChange: (id: number) =>
    api.get(`/cda/changes/${id}`),

  verifyChange: (id: number, isAuthorised: boolean, verifiedBy: string, notes?: string) =>
    api.post(`/cda/changes/${id}/verify`, null, {
      params: { is_authorised: isAuthorised, verified_by: verifiedBy, notes },
    }),

  getAlerts: (params?: {
    status?: string;
    severity?: string;
    municipality_id?: number;
    days?: number;
    limit?: number;
  }) =>
    api.get('/cda/alerts', { params }),

  getAlert: (id: number) =>
    api.get(`/cda/alerts/${id}`),

  acknowledgeAlert: (id: number, acknowledgedBy: string) =>
    api.post(`/cda/alerts/${id}/acknowledge`, null, {
      params: { acknowledged_by: acknowledgedBy },
    }),

  resolveAlert: (id: number, isAuthorised: boolean, resolutionNotes: string, resolvedBy: string) =>
    api.post(`/cda/alerts/${id}/resolve`, null, {
      params: { is_authorised: isAuthorised, resolution_notes: resolutionNotes, resolved_by: resolvedBy },
    }),

  dismissAlert: (id: number, reason: string, dismissedBy: string) =>
    api.post(`/cda/alerts/${id}/dismiss`, null, {
      params: { reason, dismissed_by: dismissedBy },
    }),

  getHistory: (params?: {
    bbox?: string;
    property_id?: number;
    change_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }) =>
    api.get('/cda/history', { params }),

  getStatistics: (params?: { days?: number; municipality_id?: number }) =>
    api.get('/cda/statistics', { params }),
}

export const guaApi = {
  getRecords: (params?: {
    property_id?: string;
    survey_number?: string;
    municipality_id?: number;
    limit?: number;
    offset?: number;
  }) =>
    api.get('/gua/records', { params }),

  getRecord: (id: number) =>
    api.get(`/gua/records/${id}`),

  createRecord: (data: any) =>
    api.post('/gua/records', data),

  updateRecord: (id: number, data: any) =>
    api.put(`/gua/records/${id}`, data),

  searchRecords: (params?: {
    query?: string;
    survey_number?: string;
    owner_name?: string;
    limit?: number;
  }) =>
    api.get('/gua/search', { params }),

  getAuditLogs: (params?: {
    record_id?: number;
    entity_type?: string;
    limit?: number;
  }) =>
    api.get('/gua/audit', { params }),
}

export const dashboardApi = {
  getOverview: () => api.get('/dashboard/overview'),
  getRecentAlerts: (limit?: number) => api.get('/dashboard/alerts/recent', { params: { limit } }),
  getStatistics: (params?: { days?: number }) => api.get('/dashboard/statistics', { params }),
}

export const healthApi = {
  check: () => api.get('/health'),
}
