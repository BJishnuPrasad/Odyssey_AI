import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, LayersControl, Polygon } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Layers } from 'lucide-react';

// Fix Leaflet's default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Mock Thanjavur Bounding Box for visuals
const thanjavurBounds = [
    [10.5, 78.9],
    [11.2, 79.7]
];

// Mock high-probability regions (red/orange circles)
const hotspots = [
    { pos: [10.7828, 79.1318], prob: 0.89, name: "Brihadeeswarar Proximity" },
    { pos: [10.8300, 79.2500], prob: 0.82, name: "Kaveri Basin North" },
    { pos: [10.9500, 79.3800], prob: 0.77, name: "Kumbakonam Outskirts" },
    { pos: [10.6000, 79.3000], prob: 0.85, name: "Pudukkottai Border Region" },
];

const MapTab = () => {
    return (
        <div className="content-pane" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 150px)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                    <h2>Archaeological Site Suitability</h2>
                    <p className="p-text" style={{ marginBottom: 0 }}>
                        Interactive prediction heat map for the Thanjavur district. Red indicates highest probability.
                    </p>
                </div>
                <button className="btn-secondary">
                    <Layers size={18} />
                    Export GeoTIFF
                </button>
            </div>

            <div className="map-wrapper" style={{ flex: 1, minHeight: 0, height: '100%' }}>
                <MapContainer
                    bounds={thanjavurBounds}
                    zoom={10}
                    scrollWheelZoom={true}
                    style={{ height: '100%', width: '100%' }}
                >
                    <LayersControl position="topright">
                        <LayersControl.BaseLayer checked name="Dark Matter (Default)">
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                            />
                        </LayersControl.BaseLayer>

                        <LayersControl.BaseLayer name="Satellite">
                            <TileLayer
                                attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
                                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                            />
                        </LayersControl.BaseLayer>

                        <LayersControl.Overlay checked name="Predictive Hotspots">
                            {hotspots.map((spot, idx) => (
                                <Circle
                                    key={idx}
                                    center={spot.pos}
                                    radius={4000 * spot.prob}
                                    pathOptions={{
                                        color: '#f59e0b',
                                        fillColor: spot.prob > 0.85 ? '#b45309' : '#d97706',
                                        fillOpacity: spot.prob * 0.6,
                                        weight: 2
                                    }}
                                >
                                    <Popup>
                                        <div style={{ background: '#1e293b', color: '#f8fafc', padding: '10px', borderRadius: '8px', margin: '-13px -20px' }}>
                                            <h4 style={{ margin: '0 0 5px 0', color: '#f59e0b' }}>{spot.name}</h4>
                                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                                                {(spot.prob * 100).toFixed(1)}% Match
                                            </div>
                                        </div>
                                    </Popup>
                                </Circle>
                            ))}
                        </LayersControl.Overlay>
                    </LayersControl>
                </MapContainer>
            </div>
        </div>
    );
};

export default MapTab;
