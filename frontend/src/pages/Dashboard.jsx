import React, { useEffect, useState } from 'react'
import { getCameras, getAlerts, getRelays } from '../api'
import { Camera, Bell, Wifi, AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [cameras, setCameras] = useState([])
  const [alerts, setAlerts] = useState([])
  const [relays, setRelays] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [camsRes, alertsRes, relaysRes] = await Promise.all([
          getCameras(),
          getAlerts(),
          getRelays()
        ])
        setCameras(camsRes.data)
        setAlerts(alertsRes.data)
        setRelays(relaysRes.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const onlineCameras = cameras.filter(c => c.online).length
  const unreadAlerts = alerts.filter(a => !a.read_at).length
  const onlineRelays = relays.filter(r => r.online).length

  const stats = [
    {
      label: 'Total Cameras',
      value: cameras.length,
      sub: `${onlineCameras} online`,
      icon: Camera,
      color: 'text-blue-400',
      bg: 'bg-blue-400/10'
    },
    {
      label: 'Unread Alerts',
      value: unreadAlerts,
      sub: `${alerts.length} total`,
      icon: Bell,
      color: 'text-yellow-400',
      bg: 'bg-yellow-400/10'
    },
    {
      label: 'Relay Agents',
      value: relays.length,
      sub: `${onlineRelays} online`,
      icon: Wifi,
      color: 'text-green-400',
      bg: 'bg-green-400/10'
    },
    {
      label: 'Offline Cameras',
      value: cameras.length - onlineCameras,
      sub: 'need attention',
      icon: AlertTriangle,
      color: 'text-red-400',
      bg: 'bg-red-400/10'
    }
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-white text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Welcome to NeuralWatch</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-card border border-border rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400 text-sm">{stat.label}</span>
              <div className={`w-8 h-8 ${stat.bg} rounded-lg flex items-center justify-center`}>
                <stat.icon size={16} className={stat.color} />
              </div>
            </div>
            <div className="text-white text-3xl font-bold mb-1">{stat.value}</div>
            <div className="text-gray-500 text-xs">{stat.sub}</div>
          </div>
        ))}
      </div>

      {/* Recent Alerts */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold">Recent Alerts</h2>
          <Link to="/alerts" className="text-primary text-sm hover:underline">
            View all
          </Link>
        </div>
        {alerts.length === 0 ? (
          <p className="text-gray-500 text-sm">No alerts yet</p>
        ) : (
          <div className="space-y-3">
            {alerts.slice(0, 5).map((alert) => (
              <div key={alert.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${alert.read_at ? 'bg-gray-600' : 'bg-yellow-400'}`} />
                  <div>
                    <p className="text-white text-sm capitalize">{alert.type} detected</p>
                    <p className="text-gray-500 text-xs">{new Date(alert.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${alert.read_at ? 'bg-gray-700 text-gray-400' : 'bg-yellow-400/10 text-yellow-400'}`}>
                  {alert.read_at ? 'Read' : 'New'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Camera Status */}
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold">Camera Status</h2>
          <Link to="/cameras" className="text-primary text-sm hover:underline">
            Manage
          </Link>
        </div>
        {cameras.length === 0 ? (
          <div className="text-center py-8">
            <Camera size={32} className="text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No cameras added yet</p>
            <Link to="/cameras" className="text-primary text-sm hover:underline mt-2 block">
              Add your first camera
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {cameras.map((cam) => (
              <div key={cam.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${cam.online ? 'bg-green-400' : 'bg-red-400'}`} />
                  <div>
                    <p className="text-white text-sm">{cam.name}</p>
                    <p className="text-gray-500 text-xs capitalize">{cam.brand}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${cam.online ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'}`}>
                  {cam.online ? 'Online' : 'Offline'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
