import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react'
import { cdaApi } from '../lib/api'

export default function Alerts() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [selectedAlert, setSelectedAlert] = useState<any>(null)

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts', statusFilter, severityFilter],
    queryFn: async () => {
      const response = await cdaApi.getAlerts({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        limit: 100,
      })
      return response.data
    },
  })

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: number) =>
      cdaApi.acknowledgeAlert(alertId, 'admin'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const resolveMutation = useMutation({
    mutationFn: ({ alertId, isAuthorised, notes }: { alertId: number; isAuthorised: boolean; notes: string }) =>
      cdaApi.resolveAlert(alertId, isAuthorised, notes, 'admin'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      setSelectedAlert(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Alerts</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage alerts generated from change detection</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-500 dark:text-gray-400">Status:</label>
          <select
            className="input w-40"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-500 dark:text-gray-400">Severity:</label>
          <select
            className="input w-40"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold dark:text-white">Alert List</h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {alerts?.length || 0} alerts
              </span>
            </div>

            {isLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
                ))}
              </div>
            ) : alerts && alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map((alert: any) => (
                  <div
                    key={alert.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      selectedAlert?.id === alert.id
                        ? 'border-primary-500 dark:border-primary-400 bg-primary-50 dark:bg-primary-900/30'
                        : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    }`}
                    onClick={() => setSelectedAlert(alert)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <AlertTriangle
                          className={`h-5 w-5 mt-0.5 ${
                            alert.severity === 'critical'
                              ? 'text-red-500'
                              : alert.severity === 'high'
                              ? 'text-orange-500'
                              : alert.severity === 'medium'
                              ? 'text-yellow-500'
                              : 'text-gray-400'
                          }`}
                        />
                        <div>
                          <h3 className="font-medium text-gray-900 dark:text-white">{alert.title}</h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{alert.description}</p>
                          <div className="flex items-center space-x-3 mt-2">
                            <span className={`badge ${getStatusBadgeClass(alert.status)}`}>
                              {alert.status}
                            </span>
                            <span className="text-xs text-gray-400">
                              {new Date(alert.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {alert.status === 'new' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              acknowledgeMutation.mutate(alert.id)
                            }}
                            className="btn-secondary text-sm px-3 py-1"
                          >
                            Acknowledge
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No alerts found</p>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-1">
          {selectedAlert ? (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 dark:text-white">Alert Details</h3>
              <div className="space-y-4">
                <div>
                  <label className="label">Title</label>
                  <p className="text-gray-900 dark:text-white">{selectedAlert.title}</p>
                </div>
                <div>
                  <label className="label">Description</label>
                  <p className="text-gray-900 dark:text-white">{selectedAlert.description}</p>
                </div>
                <div>
                  <label className="label">Status</label>
                  <span className={`badge ${getStatusBadgeClass(selectedAlert.status)}`}>
                    {selectedAlert.status}
                  </span>
                </div>
                <div>
                  <label className="label">Severity</label>
                  <span className={`badge ${getSeverityBadgeClass(selectedAlert.severity)}`}>
                    {selectedAlert.severity}
                  </span>
                </div>
                {selectedAlert.assigned_to && (
                  <div>
                    <label className="label">Assigned To</label>
                    <p className="text-gray-900 dark:text-white">{selectedAlert.assigned_to}</p>
                  </div>
                )}
                {selectedAlert.change_details && (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                    <h4 className="font-medium mb-2 dark:text-white">Change Details</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Type:</span>
                        <span className="capitalize dark:text-gray-300">
                          {selectedAlert.change_details.change_type?.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Area:</span>
                        <span className="dark:text-gray-300">{selectedAlert.change_details.area_sqm?.toFixed(1)} sqm</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Confidence:</span>
                        <span className="dark:text-gray-300">{((selectedAlert.change_details.confidence || 0) * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {selectedAlert.status !== 'resolved' && selectedAlert.status !== 'dismissed' && (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4 space-y-3">
                    <h4 className="font-medium dark:text-white">Resolve Alert</h4>
                    <div className="flex space-x-2">
                      <button
                        onClick={() =>
                          resolveMutation.mutate({
                            alertId: selectedAlert.id,
                            isAuthorised: true,
                            notes: 'Verified as authorised construction',
                          })
                        }
                        className="btn-primary flex-1 flex items-center justify-center space-x-2"
                      >
                        <CheckCircle className="h-4 w-4" />
                        <span>Authorised</span>
                      </button>
                      <button
                        onClick={() =>
                          resolveMutation.mutate({
                            alertId: selectedAlert.id,
                            isAuthorised: false,
                            notes: 'Unauthorised construction detected',
                          })
                        }
                        className="btn-danger flex-1 flex items-center justify-center space-x-2"
                      >
                        <XCircle className="h-4 w-4" />
                        <span>Unauthorised</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Eye className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Select an alert to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function getStatusBadgeClass(status: string): string {
  const classes: Record<string, string> = {
    new: 'badge-danger',
    acknowledged: 'badge-warning',
    resolved: 'badge-success',
    dismissed: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
  }
  return classes[status] || 'badge-info'
}

function getSeverityBadgeClass(severity: string): string {
  const classes: Record<string, string> = {
    critical: 'bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300',
    high: 'bg-orange-100 dark:bg-orange-900/50 text-orange-800 dark:text-orange-300',
    medium: 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-300',
    low: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
  }
  return classes[severity] || 'badge-info'
}
