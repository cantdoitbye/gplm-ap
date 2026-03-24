export interface Detection {
  id: number
  imagery_id: number | null
  property_id: number | null
  detection_type: string
  confidence: number
  area_sqm: number | null
  model_name: string | null
  model_version: string | null
  is_verified: boolean
  created_at: string
}

export interface DetectionResult {
  task_id: string
  status: string
  detections: DetectionItem[]
  summary: {
    total_detections: number
    by_type: Record<string, { count: number; total_area_sqm: number; avg_confidence: number }>
  }
  processing_time: number
  model_name: string
  model_version: string
  created_at: string
}

export interface DetectionItem {
  detection_id: string
  detection_type: string
  confidence: number
  bbox: number[]
  polygon: number[][] | null
  area_sqm: number | null
  centroid: number[] | null
}

export interface PDATask {
  task_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  completed_at?: string
  result?: DetectionResult
}

export interface ChangeDetection {
  id: number
  imagery_before_id: number
  imagery_after_id: number
  change_type: string
  change_category: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  confidence: number
  area_sqm: number | null
  is_verified: boolean
  is_authorised: boolean | null
  alert_generated: boolean
  alert_id: number | null
  created_at: string
}

export interface ChangeDetectionResult {
  task_id: string
  status: string
  changes: ChangeItem[]
  summary: {
    total_changes: number
    total_area_sqm: number
    by_type: Record<string, { count: number; total_area: number }>
    by_severity: Record<string, number>
  }
  processing_time: number
  before_date: string | null
  after_date: string | null
  created_at: string
}

export interface ChangeItem {
  change_id: string
  change_type: string
  change_category: string
  confidence: number
  severity: string
  geometry: object | null
  bbox: number[] | null
  area_sqm: number
  before_value: number | null
  after_value: number | null
}

export interface Alert {
  id: number
  change_detection_id: number
  title: string
  description: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  status: 'new' | 'acknowledged' | 'resolved' | 'dismissed'
  municipality_id: number | null
  assigned_to: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  created_at: string
  change_details?: {
    change_type: string | null
    change_category: string | null
    area_sqm: number | null
    confidence: number | null
    is_authorised: boolean | null
  } | null
}

export interface SatelliteImagery {
  id: number
  scene_id: string
  satellite: string | null
  sensor: string | null
  acquisition_date: string | null
  cloud_cover: number | null
  resolution_meters: number | null
  is_processed: boolean
  processing_status: string | null
  file_path: string | null
}

export interface Statistics {
  period_days: number
  total_detections: number
  verified_detections: number
  verification_rate: number
  by_type: Array<{
    detection_type: string
    count: number
    avg_confidence: number | null
    total_area_sqm: number | null
    avg_area_sqm: number | null
  }>
}

export interface ChangeStatistics {
  period_days: number
  total_changes: number
  verified_changes: number
  unverified_changes: number
  authorised_changes: number
  unauthorised_changes: number
  verification_rate: number
  by_type: Array<{
    change_type: string
    count: number
    total_area_sqm: number | null
    avg_confidence: number | null
  }>
  by_severity: Array<{
    severity: string
    count: number
  }>
  alerts: {
    by_status: Record<string, number>
  }
}
