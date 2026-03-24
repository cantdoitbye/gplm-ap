import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Building2,
  GitCompare,
  Bell,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  Eye,
  RefreshCw,
  Plus,
} from 'lucide-react'
import { pdaApi, cdaApi } from '../lib/api'
import type { Statistics, ChangeStatistics } from '../types'

interface Activity {
  type: 'detection' | 'change' | 'verification'
  title: string
  time: string
  icon: React.ReactNode
}

function DetectionBarChart({ data }: { data: { type: string; count: number; color: string }[] }) {
  const maxCount = Math.max(...data.map(d => d.count), 1)
  
  return (
    <div className="space-y-2">
      {data.map(item => (
        <div key={item.type} className="flex items-center gap-3">
          <div className="w-24 text-sm text-gray-600 dark:text-gray-400 capitalize">
            {item.type.replace('_', ' ')}
          </div>
          <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${(item.count / maxCount) * 100}%`,
                backgroundColor: item.color 
              }}
            />
          </div>
          <div className="w-12 text-sm font-medium text-gray-900 dark:text-white text-right">
            {item.count}
          </div>
        </div>
      ))}
    </div>
  )
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const width = 80
  const height = 24
  
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(' ')
  
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  )
}

function ActivityTimeline({ activities }: { activities: Activity[] }) {
  return (
    <div className="relative">
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />
      {activities.map((activity, index) => (
        <div key={index} className="relative flex items-start gap-4 pb-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center z-10 ${
            activity.type === 'detection' ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' :
            activity.type === 'change' ? 'bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400' :
            'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
          }`}>
            {activity.icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white">{activity.title}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{activity.time}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  loading,
  trend,
  sparklineData,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color: 'blue' | 'purple' | 'red' | 'green'
  loading?: boolean
  trend?: { value: number; isPositive: boolean }
  sparklineData?: number[]
}) {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400',
    purple: 'bg-purple-50 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400',
    red: 'bg-red-50 dark:bg-red-900/50 text-red-600 dark:text-red-400',
    green: 'bg-green-50 dark:bg-green-900/50 text-green-600 dark:text-green-400',
  }
  
  const sparklineColors = {
    blue: '#3b82f6',
    purple: '#9333ea',
    red: '#ef4444',
    green: '#22c55e',
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          {loading ? (
            <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mt-1" />
          ) : (
            <div className="flex items-center gap-2">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
              {trend && (
                <div className={`flex items-center text-sm ${
                  trend.isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {trend.isPositive ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  <span>{Math.abs(trend.value)}%</span>
                </div>
              )}
            </div>
          )}
          {sparklineData && !loading && (
            <div className="mt-2">
              <Sparkline data={sparklineData} color={sparklineColors[color]} />
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  )
}

function QuickAction({
  title,
  description,
  icon: Icon,
  link,
}: {
  title: string
  description: string
  icon: React.ElementType
  link: string
}) {
  return (
    <Link
      to={link}
      className="card hover:shadow-lg transition-shadow group"
    >
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-primary-50 dark:bg-primary-900/50 rounded-lg group-hover:bg-primary-100 dark:group-hover:bg-primary-900/70 transition-colors">
          <Icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        </div>
      </div>
    </Link>
  )
}

const mockTrends = {
  totalDetections: { value: 12, isPositive: true },
  changesDetected: { value: 8, isPositive: true },
  newAlerts: { value: 5, isPositive: false },
  verificationRate: { value: 3, isPositive: true },
}

const mockSparklineData = {
  totalDetections: [45, 52, 48, 61, 55, 58, 62],
  changesDetected: [12, 15, 18, 14, 20, 22, 25],
  newAlerts: [8, 6, 9, 7, 10, 8, 5],
  verificationRate: [85, 87, 86, 88, 89, 91, 92],
}

const mockActivities: Activity[] = [
  { type: 'detection', title: 'New building detected in Zone A', time: '2 minutes ago', icon: <Building2 className="h-4 w-4" /> },
  { type: 'change', title: 'Significant change detected on Plot #1234', time: '15 minutes ago', icon: <GitCompare className="h-4 w-4" /> },
  { type: 'verification', title: 'Detection verified by inspector', time: '1 hour ago', icon: <CheckCircle className="h-4 w-4" /> },
  { type: 'detection', title: 'Pool structure identified at Location B', time: '2 hours ago', icon: <Building2 className="h-4 w-4" /> },
  { type: 'change', title: 'Construction progress detected', time: '3 hours ago', icon: <RefreshCw className="h-4 w-4" /> },
]

const detectionTypeColors: Record<string, string> = {
  building: '#3b82f6',
  pool: '#06b6d4',
  extension: '#8b5cf6',
  garage: '#f59e0b',
  shed: '#10b981',
  default: '#6b7280',
}

export default function Dashboard() {
  const { data: pdaStats, isLoading: pdaLoading } = useQuery({
    queryKey: ['pda-statistics'],
    queryFn: async () => {
      const response = await pdaApi.getStatistics({ days: 30 })
      return response.data as Statistics
    },
  })

  const { data: cdaStats, isLoading: cdaLoading } = useQuery({
    queryKey: ['cda-statistics'],
    queryFn: async () => {
      const response = await cdaApi.getStatistics({ days: 30 })
      return response.data as ChangeStatistics
    },
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts-recent'],
    queryFn: async () => {
      const response = await cdaApi.getAlerts({ status: 'new', limit: 5 })
      return response.data
    },
  })

  const detectionChartData = pdaStats?.by_type?.map(type => ({
    type: type.detection_type,
    count: type.count,
    color: detectionTypeColors[type.detection_type] || detectionTypeColors.default,
  })) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400">AIKOSH-5 Geospatial Property Monitoring System</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Detections"
          value={pdaStats?.total_detections ?? 0}
          icon={Building2}
          color="blue"
          loading={pdaLoading}
          trend={mockTrends.totalDetections}
          sparklineData={mockSparklineData.totalDetections}
        />
        <StatCard
          title="Changes Detected"
          value={cdaStats?.total_changes ?? 0}
          icon={GitCompare}
          color="purple"
          loading={cdaLoading}
          trend={mockTrends.changesDetected}
          sparklineData={mockSparklineData.changesDetected}
        />
        <StatCard
          title="New Alerts"
          value={cdaStats?.alerts?.by_status?.new ?? 0}
          icon={Bell}
          color="red"
          loading={cdaLoading}
          trend={mockTrends.newAlerts}
          sparklineData={mockSparklineData.newAlerts}
        />
        <StatCard
          title="Verification Rate"
          value={`${((pdaStats?.verification_rate ?? 0) * 100).toFixed(1)}%`}
          icon={CheckCircle}
          color="green"
          loading={pdaLoading}
          trend={mockTrends.verificationRate}
          sparklineData={mockSparklineData.verificationRate}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Property Detection Summary</h2>
          {pdaLoading ? (
            <div className="animate-pulse space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
              ))}
            </div>
          ) : detectionChartData.length > 0 ? (
            <DetectionBarChart data={detectionChartData} />
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-center py-4">No detections in the last 30 days</p>
          )}
          <Link
            to="/detection"
            className="block mt-4 text-center text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
          >
            View All Detections →
          </Link>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Change Detection Summary</h2>
          {cdaLoading ? (
            <div className="animate-pulse space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {cdaStats?.by_severity?.map((severity) => (
                <div
                  key={severity.severity}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <AlertTriangle
                      className={`h-5 w-5 ${
                        severity.severity === 'critical'
                          ? 'text-red-500'
                          : severity.severity === 'high'
                          ? 'text-orange-500'
                          : severity.severity === 'medium'
                          ? 'text-yellow-500'
                          : 'text-gray-400'
                      }`}
                    />
                    <span className="font-medium capitalize dark:text-white">{severity.severity}</span>
                  </div>
                  <div className="text-lg font-semibold dark:text-white">{severity.count}</div>
                </div>
              ))}
              {(!cdaStats?.by_severity || cdaStats.by_severity.length === 0) && (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">No changes in the last 30 days</p>
              )}
            </div>
          )}
          <Link
            to="/changes"
            className="block mt-4 text-center text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
          >
            View All Changes →
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Recent Activity</h2>
          <ActivityTimeline activities={mockActivities} />
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold dark:text-white">Recent Alerts</h2>
            <Link to="/alerts" className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium text-sm">
              View All →
            </Link>
          </div>
          {alerts && alerts.length > 0 ? (
            <div className="space-y-3">
              {alerts.map((alert: any) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <div className="flex items-center space-x-3">
                    <AlertTriangle
                      className={`h-5 w-5 ${
                        alert.severity === 'critical'
                          ? 'text-red-500'
                          : alert.severity === 'high'
                          ? 'text-orange-500'
                          : 'text-yellow-500'
                      }`}
                    />
                    <div>
                      <div className="font-medium dark:text-white">{alert.title}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">{alert.description}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`badge ${
                        alert.status === 'new'
                          ? 'badge-danger'
                          : alert.status === 'acknowledged'
                          ? 'badge-warning'
                          : 'badge-success'
                      }`}
                    >
                      {alert.status}
                    </span>
                    <div className="text-xs text-gray-400 mt-1">
                      {new Date(alert.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No new alerts</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickAction
          title="Run Detection"
          description="Detect properties from satellite imagery"
          icon={Building2}
          link="/detection"
        />
        <QuickAction
          title="Compare Imagery"
          description="Detect changes between two dates"
          icon={GitCompare}
          link="/changes"
        />
        <QuickAction
          title="View Map"
          description="Explore detections on the map"
          icon={TrendingUp}
          link="/map"
        />
      </div>
    </div>
  )
}
