import { useState } from 'react'
import { Bell } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import NotificationDropdown from './NotificationDropdown'

interface Notification {
  id: string
  title: string
  message: string | null
  type: string
  is_read: boolean
  created_at: string
  related_entity_type?: string
  related_entity_id?: string
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)

  const { data: unreadCount = 0 } = useQuery({
    queryKey: ['unread-count'],
    queryFn: async () => {
      const response = await api.get('/notifications/unread-count')
      return response.data.count || 0
    },
    refetchInterval: 30000,
  })

  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: async () => {
      const response = await api.get('/notifications', {
        params: { limit: 10 },
      })
      return response.data
    },
    refetchInterval: 30000,
  })

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-xs font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <NotificationDropdown
          notifications={notifications}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}
