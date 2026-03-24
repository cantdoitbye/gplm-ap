import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, CircleMarker, GeoJSON } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { Layers, Building2, AlertTriangle, Satellite, Search, MapPin, X, Sliders } from 'lucide-react'
import { pdaApi, cdaApi, guaApi } from '../lib/api'
import { useTheme } from '../contexts/ThemeContext'

delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const ANDHRA_PRADESH_CENTER: [number, number] = [15.9129, 79.7400]
const DEFAULT_ZOOM = 8

const LIGHT_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const DARK_TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
const SATELLITE_TILE_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

const detectionTypeColors: Record<string, string> = {
  building: '#3b82f6',
  road: '#10b981',
  water: '#06b6d4',
  vegetation: '#22c55e',
  construction: '#f59e0b',
  default: '#8b5cf6',
}

interface LayerControlsProps {
  showSatellite: boolean
  setShowSatellite: (v: boolean) => void
  showDetections: boolean
  setShowDetections: (v: boolean) => void
  showBoundaries: boolean
  setShowBoundaries: (v: boolean) => void
  showChangeOverlay: boolean
  setShowChangeOverlay: (v: boolean) => void
  changeOpacity: number
  setChangeOpacity: (v: number) => void
}

function LayerControls({
  showSatellite,
  setShowSatellite,
  showDetections,
  setShowDetections,
  showBoundaries,
  setShowBoundaries,
  showChangeOverlay,
  setShowChangeOverlay,
  changeOpacity,
  setChangeOpacity,
}: LayerControlsProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="absolute top-4 right-4 z-[1000]">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <Sliders className="h-4 w-4 text-gray-600 dark:text-gray-300" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Layers</span>
      </button>
      {isOpen && (
        <div className="absolute top-12 right-0 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white border-b dark:border-gray-700 pb-2">
            Map Layers
          </h4>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={showSatellite}
              onChange={(e) => setShowSatellite(e.target.checked)}
              className="rounded border-gray-300 text-primary-600"
            />
            <Satellite className="h-4 w-4 text-green-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">Satellite View</span>
          </label>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={showDetections}
              onChange={(e) => setShowDetections(e.target.checked)}
              className="rounded border-gray-300 text-primary-600"
            />
            <Building2 className="h-4 w-4 text-blue-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">Detection Markers</span>
          </label>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={showBoundaries}
              onChange={(e) => setShowBoundaries(e.target.checked)}
              className="rounded border-gray-300 text-primary-600"
            />
            <MapPin className="h-4 w-4 text-purple-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">Property Boundaries</span>
          </label>
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={showChangeOverlay}
              onChange={(e) => setShowChangeOverlay(e.target.checked)}
              className="rounded border-gray-300 text-primary-600"
            />
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">Change Detection</span>
          </label>
          {showChangeOverlay && (
            <div className="pt-2 border-t dark:border-gray-700">
              <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
                Change Overlay Opacity: {Math.round(changeOpacity * 100)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={changeOpacity}
                onChange={(e) => setChangeOpacity(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface SearchBoxProps {
  onSearch: (lat: number, lng: number) => void
}

function SearchBox({ onSearch }: SearchBoxProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  const handleSearch = () => {
    const coordMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/)
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1])
      const lng = parseFloat(coordMatch[2])
      if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
        onSearch(lat, lng)
        setQuery('')
        setIsOpen(false)
        return
      }
    }
    const wellKnownPlaces: Record<string, [number, number]> = {
      'vijayawada': [16.5062, 80.6480],
      'visakhapatnam': [17.6868, 83.2185],
      'guntur': [16.3067, 80.4365],
      'tirupati': [13.6288, 79.4192],
      'kakinada': [16.9891, 82.2475],
      'nellore': [14.4426, 79.9865],
      'kurnool': [15.8281, 78.0373],
      'rajahmundry': [17.0005, 81.8034],
      'ananthapur': [14.6795, 77.6019],
      'kadapa': [14.4673, 78.8242],
      'ongole': [15.5057, 80.0499],
      'eluru': [16.7108, 81.0952],
      'machilipatnam': [16.1875, 81.1387],
      'tenali': [16.2415, 80.6528],
      'proddatur': [14.7452, 78.5486],
    }
    const place = query.toLowerCase().trim()
    if (wellKnownPlaces[place]) {
      onSearch(wellKnownPlaces[place][0], wellKnownPlaces[place][1])
      setQuery('')
      setIsOpen(false)
      return
    }
    alert('Location not found. Try coordinates (lat, lng) or a city name.')
  }

  return (
    <div className="absolute top-4 left-4 z-[1000]">
      {isOpen ? (
        <div className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Coordinates or place name"
            className="w-48 text-sm bg-transparent border-none outline-none text-gray-700 dark:text-gray-200 placeholder-gray-400"
            autoFocus
          />
          <button
            onClick={handleSearch}
            className="px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
          >
            Go
          </button>
          <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <X className="h-4 w-4 text-gray-400" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center space-x-2 px-3 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <Search className="h-4 w-4 text-gray-600 dark:text-gray-300" />
          <span className="text-sm text-gray-700 dark:text-gray-200">Search</span>
        </button>
      )}
    </div>
  )
}

function MapFlyTo({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap()
  useEffect(() => {
    map.flyTo([lat, lng], 13)
  }, [lat, lng, map])
  return null
}

function DetectionMarkers({ detections, showDetections }: { detections: any[]; showDetections: boolean }) {
  if (!showDetections || !detections) return null

  return (
    <>
      {detections.map((detection: any) => {
        const lat = detection.latitude || ANDHRA_PRADESH_CENTER[0] + (Math.random() - 0.5) * 2
        const lng = detection.longitude || ANDHRA_PRADESH_CENTER[1] + (Math.random() - 0.5) * 2
        const color = detectionTypeColors[detection.detection_type] || detectionTypeColors.default

        return (
          <CircleMarker
            key={`detection-${detection.id}`}
            center={[lat, lng]}
            radius={8}
            pathOptions={{
              fillColor: color,
              color: '#fff',
              weight: 2,
              opacity: 1,
              fillOpacity: 0.8,
            }}
          >
            <Popup>
              <div className="p-2 min-w-[180px]">
                <h3 className="font-semibold capitalize text-gray-900">
                  {detection.detection_type}
                </h3>
                <div className="text-sm mt-2 space-y-1">
                  <p className="text-gray-600">
                    <span className="font-medium">Confidence:</span>{' '}
                    {((detection.confidence || 0) * 100).toFixed(1)}%
                  </p>
                  {detection.area_sqm && (
                    <p className="text-gray-600">
                      <span className="font-medium">Area:</span> {detection.area_sqm.toFixed(1)} sqm
                    </p>
                  )}
                  <p className="text-gray-600">
                    <span className="font-medium">Verified:</span>{' '}
                    <span className={detection.is_verified ? 'text-green-600' : 'text-orange-600'}>
                      {detection.is_verified ? 'Yes' : 'No'}
                    </span>
                  </p>
                  <p className="text-gray-600">
                    <span className="font-medium">ID:</span> {detection.id}
                  </p>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}
    </>
  )
}

function PropertyBoundaryLayer({ boundaries, showBoundaries }: { boundaries: any; showBoundaries: boolean }) {
  if (!showBoundaries || !boundaries) return null

  return (
    <GeoJSON
      key={JSON.stringify(boundaries)}
      data={boundaries}
      style={{
        color: '#8b5cf6',
        weight: 2,
        opacity: 0.8,
        fillColor: '#8b5cf6',
        fillOpacity: 0.15,
      }}
      onEachFeature={(feature, layer) => {
        if (feature.properties) {
          layer.bindPopup(`
            <div class="p-2">
              <h3 class="font-semibold">Property ${feature.properties.property_id || ''}</h3>
              <p class="text-sm text-gray-600 mt-1">Area: ${feature.properties.area_sqm?.toFixed(1) || 'N/A'} sqm</p>
              ${feature.properties.owner_name ? `<p class="text-sm text-gray-600">Owner: ${feature.properties.owner_name}</p>` : ''}
            </div>
          `)
        }
      }}
    />
  )
}

function ChangeDetectionLayer({ changes, showOverlay, opacity }: { changes: any[]; showOverlay: boolean; opacity: number }) {
  if (!showOverlay || !changes || changes.length === 0) return null

  const changeFeatures = changes.map((change: any) => ({
    type: 'Feature',
    geometry: change.geometry || {
      type: 'Polygon',
      coordinates: [
        [
          [79.7 + Math.random() * 0.2, 15.8 + Math.random() * 0.2],
          [79.75 + Math.random() * 0.2, 15.8 + Math.random() * 0.2],
          [79.75 + Math.random() * 0.2, 15.85 + Math.random() * 0.2],
          [79.7 + Math.random() * 0.2, 15.85 + Math.random() * 0.2],
          [79.7 + Math.random() * 0.2, 15.8 + Math.random() * 0.2],
        ],
      ],
    },
    properties: {
      id: change.id,
      change_type: change.change_type,
      severity: change.severity,
    },
  }))

  const changeGeoJSON = { type: 'FeatureCollection' as const, features: changeFeatures }

  return (
    <GeoJSON
      key={JSON.stringify(changeGeoJSON)}
      data={changeGeoJSON}
      style={{
        color: '#ef4444',
        weight: 2,
        opacity: opacity,
        fillColor: '#ef4444',
        fillOpacity: opacity * 0.5,
      }}
      onEachFeature={(feature, layer) => {
        if (feature.properties) {
          layer.bindPopup(`
            <div class="p-2">
              <h3 class="font-semibold capitalize">${feature.properties.change_type || 'Change'}</h3>
              <p class="text-sm text-gray-600 mt-1">Severity: ${feature.properties.severity || 'N/A'}</p>
              <p class="text-sm text-gray-600">ID: ${feature.properties.id}</p>
            </div>
          `)
        }
      }}
    />
  )
}

export default function MapView() {
  const { resolvedTheme } = useTheme()
  const [showSatellite, setShowSatellite] = useState(false)
  const [showDetections, setShowDetections] = useState(true)
  const [showBoundaries, setShowBoundaries] = useState(false)
  const [showChangeOverlay, setShowChangeOverlay] = useState(true)
  const [changeOpacity, setChangeOpacity] = useState(0.5)
  const [searchCoords, setSearchCoords] = useState<[number, number] | null>(null)
  const [selectedType, setSelectedType] = useState<string>('all')

  const { data: detections } = useQuery({
    queryKey: ['map-detections'],
    queryFn: async () => {
      const response = await pdaApi.getDetections({ limit: 200 })
      return response.data
    },
  })

  const { data: alerts } = useQuery({
    queryKey: ['map-alerts'],
    queryFn: async () => {
      const response = await cdaApi.getAlerts({ limit: 100 })
      return response.data
    },
  })

  const { data: propertyBoundaries } = useQuery({
    queryKey: ['property-boundaries'],
    queryFn: async () => {
      const response = await guaApi.getRecords({ limit: 100 })
      const features = response.data?.records?.map((record: any) => ({
        type: 'Feature',
        geometry: record.geometry || {
          type: 'Polygon',
          coordinates: [[[79.7, 15.8], [79.8, 15.8], [79.8, 15.9], [79.7, 15.9], [79.7, 15.8]]],
        },
        properties: {
          property_id: record.property_id,
          area_sqm: record.area_sqm,
          owner_name: record.owner_name,
        },
      })) || []
      return { type: 'FeatureCollection', features }
    },
  })

  const { data: changes } = useQuery({
    queryKey: ['map-changes'],
    queryFn: async () => {
      const response = await cdaApi.getChanges({ limit: 100 })
      return response.data
    },
  })

  const filteredDetections = detections?.filter((d: any) => {
    if (selectedType === 'all') return true
    return d.detection_type === selectedType
  })

  const handleSearch = (lat: number, lng: number) => {
    setSearchCoords([lat, lng])
  }

  const tileUrl = showSatellite
    ? SATELLITE_TILE_URL
    : resolvedTheme === 'dark'
    ? DARK_TILE_URL
    : LIGHT_TILE_URL

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Map View</h1>
          <p className="text-gray-500 dark:text-gray-400">Explore detections and alerts on the map</p>
        </div>
      </div>

      <div className="flex items-center space-x-4 mb-4">
        <div className="flex items-center space-x-2">
          <Layers className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter:</span>
        </div>
        <div className="border-r border-gray-200 dark:border-gray-700 pr-4">
          <select
            className="input w-40"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="building">Buildings</option>
            <option value="road">Roads</option>
            <option value="water">Water</option>
            <option value="vegetation">Vegetation</option>
            <option value="construction">Construction</option>
          </select>
        </div>
      </div>

      <div className="card p-0 overflow-hidden relative">
        <MapContainer
          center={ANDHRA_PRADESH_CENTER}
          zoom={DEFAULT_ZOOM}
          style={{ height: '600px', width: '100%' }}
          className={resolvedTheme === 'dark' ? 'dark-map' : ''}
        >
          <TileLayer
            attribution={showSatellite ? 'Tiles &copy; Esri' : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}
            url={tileUrl}
          />

          {searchCoords && <MapFlyTo lat={searchCoords[0]} lng={searchCoords[1]} />}

          <DetectionMarkers detections={filteredDetections || []} showDetections={showDetections} />
          <PropertyBoundaryLayer boundaries={propertyBoundaries} showBoundaries={showBoundaries} />
          <ChangeDetectionLayer changes={changes || []} showOverlay={showChangeOverlay} opacity={changeOpacity} />

          {showDetections && alerts?.map((alert: any) => (
            <Marker
              key={`alert-${alert.id}`}
              position={[
                alert.latitude || ANDHRA_PRADESH_CENTER[0] + (Math.random() - 0.5) * 1.5,
                alert.longitude || ANDHRA_PRADESH_CENTER[1] + (Math.random() - 0.5) * 1.5,
              ]}
            >
              <Popup>
                <div className="p-2">
                  <h3 className="font-semibold">{alert.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">{alert.description}</p>
                  <div className="text-sm mt-2 space-y-1">
                    <p>
                      <span className="font-medium">Status:</span>{' '}
                      <span className={`badge ${getAlertStatusBadge(alert.status)}`}>
                        {alert.status}
                      </span>
                    </p>
                    <p>
                      <span className="font-medium">Severity:</span>{' '}
                      <span className={`badge ${getAlertSeverityBadge(alert.severity)}`}>
                        {alert.severity}
                      </span>
                    </p>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        <SearchBox onSearch={handleSearch} />
        <LayerControls
          showSatellite={showSatellite}
          setShowSatellite={setShowSatellite}
          showDetections={showDetections}
          setShowDetections={setShowDetections}
          showBoundaries={showBoundaries}
          setShowBoundaries={setShowBoundaries}
          showChangeOverlay={showChangeOverlay}
          setShowChangeOverlay={setShowChangeOverlay}
          changeOpacity={changeOpacity}
          setChangeOpacity={setChangeOpacity}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center space-x-3">
            <Building2 className="h-8 w-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Detections Shown</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{filteredDetections?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-8 w-8 text-red-500" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Alerts Shown</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{alerts?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center space-x-3">
            <Layers className="h-8 w-8 text-purple-500" />
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Active Layers</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">
                {[showDetections, showBoundaries, showChangeOverlay].filter(Boolean).length}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function getAlertStatusBadge(status: string): string {
  const classes: Record<string, string> = {
    new: 'badge-danger',
    acknowledged: 'badge-warning',
    resolved: 'badge-success',
    dismissed: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  }
  return classes[status] || 'badge-info'
}

function getAlertSeverityBadge(severity: string): string {
  const classes: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/50 dark:text-orange-300',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300',
    low: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  }
  return classes[severity] || 'badge-info'
}
