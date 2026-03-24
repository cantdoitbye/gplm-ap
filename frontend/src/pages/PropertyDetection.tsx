import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Play, RefreshCw, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { pdaApi } from '../lib/api'
import type { PDATask, SatelliteImagery } from '../types'

export default function PropertyDetection() {
  const [selectedImagery, setSelectedImagery] = useState<number | null>(null)
  const [detectionTypes, setDetectionTypes] = useState<string[]>(['building'])
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)

  const { data: imagery } = useQuery({
    queryKey: ['imagery'],
    queryFn: async () => {
      const response = await pdaApi.getImagery({ limit: 20 })
      return response.data.imagery as SatelliteImagery[]
    },
  })

  const { data: detections } = useQuery({
    queryKey: ['detections'],
    queryFn: async () => {
      const response = await pdaApi.getDetections({ limit: 50 })
      return response.data
    },
  })

  const { data: taskStatus } = useQuery({
    queryKey: ['task-status', activeTaskId],
    queryFn: async () => {
      if (!activeTaskId) return null
      const response = await pdaApi.getStatus(activeTaskId)
      return response.data as PDATask
    },
    enabled: !!activeTaskId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 2000
    },
  })

  const detectMutation = useMutation({
    mutationFn: async () => {
      const response = await pdaApi.detect({
        imagery_id: selectedImagery || undefined,
        detection_types: detectionTypes,
        confidence_threshold: confidenceThreshold,
      })
      return response.data
    },
    onSuccess: (data) => {
      setActiveTaskId(data.task_id)
    },
  })

  const handleDetect = () => {
    detectMutation.mutate()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Property Detection</h1>
          <p className="text-gray-500 dark:text-gray-400">Detect buildings, roads, and water bodies from satellite imagery</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Detection Configuration</h2>
            
            <div className="space-y-4">
              <div>
                <label className="label">Satellite Imagery</label>
                <select
                  className="input"
                  value={selectedImagery || ''}
                  onChange={(e) => setSelectedImagery(Number(e.target.value) || null)}
                >
                  <option value="">Select imagery...</option>
                  {imagery?.map((img) => (
                    <option key={img.id} value={img.id}>
                      {img.scene_id} - {img.acquisition_date ? new Date(img.acquisition_date).toLocaleDateString() : 'N/A'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label">Detection Types</label>
                <div className="space-y-2">
                  {['building', 'road', 'water'].map((type) => (
                    <label key={type} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={detectionTypes.includes(type)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setDetectionTypes([...detectionTypes, type])
                          } else {
                            setDetectionTypes(detectionTypes.filter((t) => t !== type))
                          }
                        }}
                        className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="capitalize dark:text-gray-300">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="label">Confidence Threshold: {confidenceThreshold}</label>
                <input
                  type="range"
                  min="0.1"
                  max="0.95"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <button
                onClick={handleDetect}
                disabled={detectMutation.isPending || detectionTypes.length === 0}
                className="btn-primary w-full flex items-center justify-center space-x-2"
              >
                {detectMutation.isPending ? (
                  <>
                    <RefreshCw className="h-5 w-5 animate-spin" />
                    <span>Running...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5" />
                    <span>Run Detection</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {taskStatus && (
            <div className="card">
              <h3 className="font-semibold mb-3 dark:text-white">Task Status</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Status</span>
                  <TaskStatusBadge status={taskStatus.status} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Progress</span>
                  <span className="font-medium dark:text-white">{taskStatus.progress}%</span>
                </div>
                {taskStatus.message && (
                  <p className="text-sm text-gray-600 dark:text-gray-300">{taskStatus.message}</p>
                )}
                {taskStatus.status === 'completed' && taskStatus.result && (
                  <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
                    <p className="text-sm text-green-800 dark:text-green-300">
                      Found {taskStatus.result.summary.total_detections} objects
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Recent Detections</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Confidence
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Area (sqm)
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Verified
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {detections?.map((detection: any) => (
                    <tr key={detection.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-3 py-4 whitespace-nowrap">
                        <span className="badge badge-info capitalize">
                          {detection.detection_type}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap dark:text-gray-300">
                        {((detection.confidence || 0) * 100).toFixed(1)}%
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap dark:text-gray-300">
                        {detection.area_sqm ? detection.area_sqm.toFixed(1) : '-'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap">
                        {detection.is_verified ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <Clock className="h-5 w-5 text-gray-400" />
                        )}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(detection.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!detections || detections.length === 0) && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No detections yet. Run a detection task to get started.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TaskStatusBadge({ status }: { status: string }) {
  const statusConfig = {
    queued: { icon: Clock, color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-700' },
    processing: { icon: RefreshCw, color: 'text-blue-500 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/50' },
    completed: { icon: CheckCircle, color: 'text-green-500 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/50' },
    failed: { icon: AlertCircle, color: 'text-red-500 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/50' },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.queued
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
      <Icon className={`h-3 w-3 mr-1 ${status === 'processing' ? 'animate-spin' : ''}`} />
      {status}
    </span>
  )
}
