import React, { useEffect, useState } from 'react'
import { getCameras, addCamera, deleteCamera } from '../api'
import { Camera, Plus, Trash2, Wifi, WifiOff, X } from 'lucide-react'

export default function Cameras() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', rtsp_url: '', brand: 'generic' })
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const brands = ['generic','hikvision','dahua','cpplus','reolink','tapo','axis','uniview','hanwha','bosch']

  const fetchCameras = async () => {
    try {
      const res = await getCameras()
      setCameras(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCameras() }, [])

  const handleAdd = async (e) => {
    e.preventDefault()
    setAdding(true)
    setError('')
    try {
      await addCamera(form)
      setShowModal(false)
      setForm({ name: '', rtsp_url: '', brand: 'generic' })
      fetchCameras()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add camera')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this camera?')) return
    try {
      await deleteCamera(id)
      fetchCameras()
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-white text-2xl font-bold">Cameras</h1>
          <p className="text-gray-400 text-sm mt-1">{cameras.length} camera(s) registered</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-primary hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Add Camera
        </button>
      </div>

      {/* Camera Grid */}
      {cameras.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-16 text-center">
          <Camera size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-white font-medium mb-2">No cameras yet</p>
          <p className="text-gray-500 text-sm mb-4">Add your first IP camera to get started</p>
          <button
            onClick={() => setShowModal(true)}
            className="bg-primary hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            Add Camera
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cameras.map((cam) => (
            <div key={cam.id} className="bg-card border border-border rounded-xl p-6">
              {/* Camera preview placeholder */}
              <div className="w-full h-40 bg-dark rounded-lg mb-4 flex items-center justify-center border border-border">
                {cam.online ? (
                  <div className="text-center">
                    <Wifi size={24} className="text-green-400 mx-auto mb-2" />
                    <p className="text-green-400 text-xs">Live</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <WifiOff size={24} className="text-gray-600 mx-auto mb-2" />
                    <p className="text-gray-600 text-xs">Offline</p>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-white font-medium">{cam.name}</h3>
                  <p className="text-gray-500 text-xs capitalize mt-0.5">{cam.brand}</p>
                  <p className="text-gray-600 text-xs mt-1 truncate max-w-[180px]">{cam.rtsp_url}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${cam.online ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'}`}>
                    {cam.online ? 'Online' : 'Offline'}
                  </span>
                  <button
                    onClick={() => handleDelete(cam.id)}
                    className="text-gray-600 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Stats */}
              {cam.fps && (
                <div className="flex gap-4 mt-3 pt-3 border-t border-border">
                  <div>
                    <p className="text-gray-500 text-xs">FPS</p>
                    <p className="text-white text-sm font-medium">{cam.fps}</p>
                  </div>
                  {cam.resolution && (
                    <div>
                      <p className="text-gray-500 text-xs">Resolution</p>
                      <p className="text-white text-sm font-medium">{cam.resolution}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add Camera Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-2xl p-8 w-full max-w-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-white font-semibold text-lg">Add Camera</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white">
                <X size={20} />
              </button>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="text-gray-400 text-sm mb-1.5 block">Camera Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-dark border border-border rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-primary"
                  placeholder="Front Door"
                  required
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-1.5 block">RTSP URL</label>
                <input
                  type="text"
                  value={form.rtsp_url}
                  onChange={(e) => setForm({ ...form, rtsp_url: e.target.value })}
                  className="w-full bg-dark border border-border rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-primary"
                  placeholder="rtsp://192.168.1.100:554/stream1"
                  required
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-1.5 block">Brand</label>
                <select
                  value={form.brand}
                  onChange={(e) => setForm({ ...form, brand: e.target.value })}
                  className="w-full bg-dark border border-border rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-primary"
                >
                  {brands.map(b => (
                    <option key={b} value={b} className="capitalize">{b}</option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={adding}
                className="w-full bg-primary hover:bg-blue-700 text-white font-medium py-3 rounded-lg transition-colors disabled:opacity-50"
              >
                {adding ? 'Adding...' : 'Add Camera'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
