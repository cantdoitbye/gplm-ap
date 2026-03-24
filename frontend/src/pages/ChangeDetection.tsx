import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Play, RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { cdaApi } from '../lib/api'
import type { ChangeStatistics } from '../types'

export default function ChangeDetection() {
  const [beforeImageryId, setBeforeImageryId] = useState<number>(1)
  const [afterImageryId, setAfterImageryId] = useState<number>(2)
  const [changeTypes, setChangeTypes] = useState<string[]>(['new_construction', 'expansion'])
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)

  const { data: statistics } = useQuery({
    queryKey: ['change-statistics'],
    queryFn: async () => {
      const response = await cdaApi.getStatistics({ days: 30 })
      return response.data as ChangeStatistics
    },
  })

  const { data: changes } = useQuery({
    queryKey: ['changes'],
    queryFn: async () => {
      const response = await cdaApi.getChanges({ limit: 50 })
      return response.data
    },
  })

  const { data: taskStatus } = useQuery({
    queryKey: ['change-task-status', activeTaskId],
    queryFn: async () => {
      if (!activeTaskId) return null
      const response = await cdaApi.getStatus(activeTaskId)
      return response.data
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

  const compareMutation = useMutation({
    mutationFn: async () => {
      const response = await cdaApi.compare({
        imagery_before_id: beforeImageryId,
        imagery_after_id: afterImageryId,
        change_types: changeTypes,
      })
      return response.data
    },
    onSuccess: (data) => {
      setActiveTaskId(data.task_id)
    },
  })

  const handleCompare = () => {
    compareMutation.mutate()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Change Detection</h1>
          <p className="text-gray-500 dark:text-gray-400">Compare satellite imagery to detect changes over time</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Changes"
          value={statistics?.total_changes ?? 0}
          color="blue"
        />
        <StatCard
          title="Verified"
          value={statistics?.verified_changes ?? 0}
          color="green"
        />
        <StatCard
          title="Authorised"
          value={statistics?.authorised_changes ?? 0}
          color="purple"
        />
        <StatCard
          title="Unauthorised"
          value={statistics?.unauthorised_changes ?? 0}
          color="red"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Comparison Configuration</h2>
            
            <div className="space-y-4">
              <div>
                <label className="label">Before Imagery ID</label>
                <input
                  type="number"
                  className="input"
                  value={beforeImageryId}
                  onChange={(e) => setBeforeImageryId(Number(e.target.value))}
                  min="1"
                />
              </div>

              <div>
                <label className="label">After Imagery ID</label>
                <input
                  type="number"
                  className="input"
                  value={afterImageryId}
                  onChange={(e) => setAfterImageryId(Number(e.target.value))}
                  min="1"
                />
              </div>

              <div>
                <label className="label">Change Types</label>
                <div className="space-y-2">
                  {['new_construction', 'expansion', 'demolition', 'vegetation_change'].map((type) => (
                    <label key={type} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={changeTypes.includes(type)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setChangeTypes([...changeTypes, type])
                          } else {
                            setChangeTypes(changeTypes.filter((t) => t !== type))
                          }
                        }}
                        className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="capitalize dark:text-gray-300">{type.replace('_', ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                onClick={handleCompare}
                disabled={compareMutation.isPending || changeTypes.length === 0}
                className="btn-primary w-full flex items-center justify-center space-x-2"
              >
                {compareMutation.isPending ? (
                  <>
                    <RefreshCw className="h-5 w-5 animate-spin" />
                    <span>Comparing...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5" />
                    <span>Run Comparison</span>
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
                  <span className={`badge ${taskStatus.status === 'completed' ? 'badge-success' : 'badge-info'}`}>
                    {taskStatus.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">Progress</span>
                  <span className="font-medium dark:text-white">{taskStatus.progress}%</span>
                </div>
                {taskStatus.status === 'completed' && taskStatus.result && (
                  <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/30 rounded-lg">
                    <p className="text-sm text-green-800 dark:text-green-300">
                      Found {taskStatus.result.summary?.total_changes || 0} changes
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Detected Changes</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Change Type
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Severity
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Area (sqm)
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Authorised
                    </th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {changes?.map((change: any) => (
                    <tr key={change.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-3 py-4 whitespace-nowrap">
                        <span className="badge badge-info capitalize">
                          {change.change_type?.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap">
                        <SeverityBadge severity={change.severity} />
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap dark:text-gray-300">
                        {change.area_sqm ? change.area_sqm.toFixed(1) : '-'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap">
                        {change.is_authorised === true ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : change.is_authorised === false ? (
                          <XCircle className="h-5 w-5 text-red-500" />
                        ) : (
                          <span className="text-gray-400">Pending</span>
                        )}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {new Date(change.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!changes || changes.length === 0) && (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No changes detected yet. Run a comparison to get started.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/50',
    green: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/50',
    purple: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/50',
    red: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/50',
  }

  return (
    <div className="card">
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</p>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300',
    high: 'bg-orange-100 dark:bg-orange-900/50 text-orange-800 dark:text-orange-300',
    medium: 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300',
    low: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
  }

  return (
    <span className={`badge ${colors[severity] || colors.low} capitalize`}>
      <AlertTriangle className="h-3 w-3 mr-1" />
      {severity}
    </span>
  )
}
