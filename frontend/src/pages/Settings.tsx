import { useState } from 'react'
import { Settings as SettingsIcon, Save, RefreshCw, Sun, Moon, Monitor } from 'lucide-react'
import { healthApi } from '../lib/api'
import { useQuery } from '@tanstack/react-query'
import { useTheme, type ThemeMode } from '../contexts/ThemeContext'

export default function Settings() {
  const { themeMode, setThemeMode } = useTheme()
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5)
  const [alertSeverity, setAlertSeverity] = useState('medium')
  const [notificationsEnabled, setNotificationsEnabled] = useState(true)

  const { data: health, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await healthApi.check()
      return response.data
    },
  })

  const themeOptions: { value: ThemeMode; label: string; icon: React.ElementType; description: string }[] = [
    { value: 'light', label: 'Light', icon: Sun, description: 'Always use light theme' },
    { value: 'dark', label: 'Dark', icon: Moon, description: 'Always use dark theme' },
    { value: 'system', label: 'System', icon: Monitor, description: 'Follow system preference' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
          <p className="text-gray-500 dark:text-gray-400">Configure system preferences</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2 dark:text-white">
            <Sun className="h-5 w-5" />
            <span>Appearance</span>
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="label">Theme Preference</label>
              <div className="grid grid-cols-3 gap-3 mt-2">
                {themeOptions.map((option) => {
                  const Icon = option.icon
                  return (
                    <button
                      key={option.value}
                      onClick={() => setThemeMode(option.value)}
                      className={`flex flex-col items-center p-4 rounded-lg border-2 transition-all ${
                        themeMode === option.value
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <Icon className={`h-6 w-6 mb-2 ${
                        themeMode === option.value
                          ? 'text-primary-600 dark:text-primary-400'
                          : 'text-gray-400 dark:text-gray-500'
                      }`} />
                      <span className={`text-sm font-medium ${
                        themeMode === option.value
                          ? 'text-primary-700 dark:text-primary-300'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {option.label}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-center">
                        {option.description}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2 dark:text-white">
            <SettingsIcon className="h-5 w-5" />
            <span>Detection Settings</span>
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="label">Default Confidence Threshold</label>
              <input
                type="range"
                min="0.1"
                max="0.95"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full"
              />
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Current: {(confidenceThreshold * 100).toFixed(0)}%
              </p>
            </div>

            <div>
              <label className="label">Minimum Alert Severity</label>
              <select
                className="input"
                value={alertSeverity}
                onChange={(e) => setAlertSeverity(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical Only</option>
              </select>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Alerts will only be generated for changes at or above this severity level
              </p>
            </div>

            <div>
              <label className="label">Enable Notifications</label>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
                    notificationsEnabled ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-600'
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      notificationsEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {notificationsEnabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2 dark:text-white">
            <RefreshCw className="h-5 w-5" />
            <span>System Status</span>
          </h2>
          
          <div className="space-y-4">
            <button
              onClick={() => refetchHealth()}
              className="btn-secondary flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Refresh Status</span>
            </button>

            {health && (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <span className="text-sm font-medium dark:text-gray-300">Status</span>
                  <span className={`badge ${health.status === 'healthy' ? 'badge-success' : 'badge-danger'}`}>
                    {health.status}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <span className="text-sm font-medium dark:text-gray-300">Version</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">{health.version}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <span className="text-sm font-medium dark:text-gray-300">Timestamp</span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {new Date(health.timestamp).toLocaleString()}
                  </span>
                </div>
                
                {health.services && (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-3">
                    <h3 className="text-sm font-medium mb-2 dark:text-white">Services</h3>
                    <div className="space-y-2">
                      {Object.entries(health.services).map(([service, status]) => (
                        <div
                          key={service}
                          className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700/50 rounded"
                        >
                          <span className="text-sm capitalize dark:text-gray-300">{service}</span>
                          <span className={`badge ${status === 'healthy' ? 'badge-success' : 'badge-warning'}`}>
                            {status as string}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="card lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">About AIKOSH-5</h2>
          <div className="prose prose-sm max-w-none text-gray-600 dark:text-gray-400">
            <p>
              AIKOSH-5 is an AI-Enabled Geospatial Property & Land-Use Monitoring System 
              designed for Andhra Pradesh's urban local bodies (ULBs).
            </p>
            <h3 className="text-md font-semibold mt-4 dark:text-white">Key Features</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>Property Detection Agent (PDA): Detects buildings, roads, and water bodies from satellite imagery</li>
              <li>Change Detection Agent (CDA): Identifies new construction, expansions, demolitions, and encroachments</li>
              <li>GIS Auto-Update Agent (GUA): Automatically updates property records based on verified changes</li>
              <li>Trust Score System: Ensures data quality and verification through a multi-dimensional scoring system</li>
              <li>Blockchain-style Audit Trail: Maintains immutable records of all changes</li>
            </ul>
            <h3 className="text-md font-semibold mt-4 dark:text-white">Data Sources</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>Satellite Imagery: Sentinel-2 via Copernicus Data Space</li>
              <li>Building Footprints: Google Open Buildings</li>
              <li>Administrative Boundaries: OpenStreetMap</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button className="btn-primary flex items-center space-x-2">
          <Save className="h-5 w-5" />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  )
}
