import React, { useEffect, useState } from 'react'
import { getAlerts, dismissAlert, confirmAlert } from '../api'
import { Bell, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAlerts = async () => {
    try {
      const res = await getAlerts()
      setAlerts(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAlerts() }, [])

  const handleDismiss = async (id) => {
    try {
      await dismissAlert(id)
      fetchAlerts()
    } catch (err) {
      console.error(err)
    }
  }

  const handleConfirm = async (id) => {
    try {
      await confirmAlert(id)
      fetchAlerts()
    } catch (err) {
      console.error(err)
    }
  }

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
        <h1 className="text-white text-2xl font-bold">Alerts</h1>
        <p className="text-gray-400 text-sm mt-1">
          {alerts.filter(a => !a.read_at).length} unread alerts
        </p>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-16 text-center">
          <Bell size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-white font-medium mb-2">No alerts yet</p>
          <p className="text-gray-500 text-sm">Alerts will appear here when motion is detected</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`bg-card border rounded-xl p-5 flex items-center justify-between ${
                alert.read_at ? 'border-border' : 'border-yellow-400/30'
              }`}
            >
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  alert.false_positive
                    ? 'bg-gray-700'
                    : alert.read_at
                    ? 'bg-green-400/10'
                    : 'bg-yellow-400/10'
                }`}>
                  <AlertTriangle size={18} className={
                    alert.false_positive
                      ? 'text-gray-400'
                      : alert.read_at
                      ? 'text-green-400'
                      : 'text-yellow-400'
                  } />
                </div>
                <div>
                  <p className="text-white text-sm font-medium capitalize">
                    {alert.type} detected
                  </p>
                  <p className="text-gray-500 text-xs mt-0.5">
                    {new Date(alert.created_at).toLocaleString()}
                  </p>
                  {alert.payload?.camera_name && (
                    <p className="text-gray-600 text-xs mt-0.5">
                      Camera: {alert.payload.camera_name}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {!alert.read_at && (
                  <>
                    <button
                      onClick={() => handleConfirm(alert.id)}
                      className="flex items-center gap-1.5 bg-green-400/10 hover:bg-green-400/20 text-green-400 px-3 py-1.5 rounded-lg text-xs transition-colors"
                    >
                      <CheckCircle size={14} />
                      Confirm
                    </button>
                    <button
                      onClick={() => handleDismiss(alert.id)}
                      className="flex items-center gap-1.5 bg-red-400/10 hover:bg-red-400/20 text-red-400 px-3 py-1.5 rounded-lg text-xs transition-colors"
                    >
                      <XCircle size={14} />
                      Dismiss
                    </button>
                  </>
                )}
                {alert.read_at && (
                  <span className={`text-xs px-3 py-1.5 rounded-lg ${
                    alert.false_positive
                      ? 'bg-gray-700 text-gray-400'
                      : 'bg-green-400/10 text-green-400'
                  }`}>
                    {alert.false_positive ? 'Dismissed' : 'Confirmed'}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
