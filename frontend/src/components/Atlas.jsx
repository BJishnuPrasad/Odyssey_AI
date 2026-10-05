import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, ImageOverlay, useMap, useMapEvents, ScaleControl } from 'react-leaflet'
import L from 'leaflet'
import { Layers, Maximize, MapPin } from 'lucide-react'
import { artifactUrl, request } from '../api'
import './environment.css'

function Controls({ boundary, onInspect, focusSite, reset, runId }) {
  const map = useMap()
  useEffect(() => {
    const attribution = 'Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    map.attributionControl.addAttribution(attribution)
    return () => map.attributionControl.removeAttribution(attribution)
  }, [map])
  useMapEvents({ click: e => onInspect(e.latlng) })
  useEffect(() => {
    if (boundary) map.fitBounds(L.geoJSON(boundary).getBounds(), { padding: [25, 25] })
  }, [map, boundary, reset, runId])
  useEffect(() => {
    if (focusSite) { const [lng, lat] = focusSite.geometry.coordinates; map.flyTo([lat, lng], 13) }
  }, [map, focusSite])
  return null
}

export default function Atlas({ boundary, sites, report, runId, mode, onInspect, focusSite, onOpenSite }) {
  const [showSites, setShowSites] = useState(true)
  const [showWater, setShowWater] = useState(false)
  const [basemap, setBasemap] = useState(false)
  const [tileError, setTileError] = useState(false)
  const [water, setWater] = useState(null)
  const [waterError, setWaterError] = useState('')
  const [reset, setReset] = useState(0)
  const [evidenceId, setEvidenceId] = useState('')
  const evidenceLayer = report?.environment?.layers.find(l => l.id === evidenceId)
  useEffect(() => {
    if (!showWater || water) return
    let ignore = false
    request('/layers/water').then(data => { if (!ignore) setWater(data) }).catch(error => { if (!ignore) setWaterError(error.message) })
    return () => { ignore = true }
  }, [showWater, water])
  return <div className="map-wrap">
    <MapContainer center={[10.77, 79.18]} zoom={9} minZoom={7} maxZoom={17} className="atlas-map" scrollWheelZoom={true} preferCanvas={true}>
      {basemap && <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' eventHandlers={{ tileerror: () => setTileError(true) }} />}
      {report && <ImageOverlay url={artifactUrl(runId, mode === 'terrain' ? 'overlay.png' : 'evidence.png')} bounds={report.overlay_bounds} opacity={0.85} />}
      {evidenceLayer && <ImageOverlay url={artifactUrl(runId,evidenceLayer.image)} bounds={evidenceLayer.bounds} opacity={.9} />}
      {boundary && <GeoJSON data={boundary} style={{ color: '#344f48', weight: 1.8, fillColor: '#e7e6d4', fillOpacity: report ? 0 : 0.25, dashArray: '4 3' }} />}
      {showWater && water && <GeoJSON data={water} style={{ color: '#297ca4', weight: 1.4, fillOpacity: 0.3 }} />}
      {showSites && sites?.features.map(f => <CircleMarker key={f.properties.osm_id} center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]} radius={5.5} pathOptions={{ color: '#fff', weight: 2, fillColor: '#8b533c', fillOpacity: 1 }}><Popup><strong>{f.properties.name}</strong><p>Recorded heritage · {f.properties.category}</p><small>OSM location; not field verified.</small><p><button className="text-button" onClick={() => onOpenSite(f.properties.osm_id.replace('/', '-'))}>Open 3D & soil profile</button></p></Popup></CircleMarker>)}
      <Controls boundary={boundary} onInspect={onInspect} focusSite={focusSite} reset={reset} runId={runId} />
      <ScaleControl position="bottomleft" imperial={false} />
    </MapContainer>
    {report?.environment?.layers.length > 0 && <div className="atlas-evidence-selector"><label htmlFor="atlas-evidence">Run evidence overlay</label><select id="atlas-evidence" value={evidenceLayer ? evidenceId : ''} onChange={event => setEvidenceId(event.target.value)}><option value="">Terrain / evidence classification</option>{report.environment.layers.map(layer => <option key={layer.id} value={layer.id}>{layer.title}</option>)}</select>{evidenceLayer && <small>{evidenceLayer.title} · {evidenceLayer.range.join(' to ')} {evidenceLayer.units} · acquired data, not a suitability score</small>}</div>}
    <div className="map-layers"><div><Layers size={15} /><strong>Map layers</strong><button aria-label="Fit district boundary" onClick={() => setReset(n => n+1)}><Maximize size={15} /></button></div><label><input type="checkbox" checked={showSites} onChange={e => setShowSites(e.target.checked)} /><span className="layer-dot heritage" />Heritage locations</label><label><input type="checkbox" checked={showWater} onChange={e => setShowWater(e.target.checked)} /><span className="layer-dot water" />Mapped water</label><label><input type="checkbox" checked={basemap} onChange={e => setBasemap(e.target.checked)} /><span className="layer-dot base" />Online basemap</label>{waterError && showWater && <small role="alert">{waterError}</small>}</div>
    <div className="map-region"><MapPin size={14} /> THANJAVUR DISTRICT</div>
    {(tileError && basemap) && <div className="map-offline">Basemap tiles unavailable. Local research layers remain available.</div>}
    {!report && <div className="map-empty-note">District & heritage context · run an analysis to add terrain zones</div>}
  </div>
}
