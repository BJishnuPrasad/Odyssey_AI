import React from 'react';
import { Database, Server, Component, Cpu, ArrowRight } from 'lucide-react';

const ArchitectureTab = () => {
    return (
        <div className="content-pane">
            <div style={{ marginBottom: '3rem' }}>
                <h2>System Architecture</h2>
                <p className="p-text">
                    Odyssey AI is driven by a highly modular, scalable data pipeline. From raw geospatial ingestion
                    to final machine learning prediction maps, every component runs asynchronously.
                </p>
            </div>

            <div className="grid-2">
                {/* Step 1 */}
                <div className="card" style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
                        <div style={{
                            background: 'rgba(217, 119, 6, 0.15)',
                            padding: '1rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(217, 119, 6, 0.3)'
                        }}>
                            <Database size={32} color="#f59e0b" />
                        </div>
                        <div>
                            <h3>1. Data Ingestion & Fallback Layer</h3>
                            <p className="p-text" style={{ fontSize: '0.95rem' }}>
                                Ingests high-resolution DEM (Digital Elevation Models) and OSM PBF extractions.
                                Utilizes conditional pyrosm loaders with manual GeoPandas fallbacks for robustness across environments.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Step 2 */}
                <div className="card" style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
                        <div style={{
                            background: 'rgba(217, 119, 6, 0.15)',
                            padding: '1rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(217, 119, 6, 0.3)'
                        }}>
                            <Component size={32} color="#f59e0b" />
                        </div>
                        <div>
                            <h3>2. Grid & Feature Engineering</h3>
                            <p className="p-text" style={{ fontSize: '0.95rem' }}>
                                Generates a 250m uniform sampling grid across the district. Interpolates distance-to-waterways, roads,
                                calculates slopes, and applies categorical encodings to environmental markers.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Step 3 */}
                <div className="card" style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
                        <div style={{
                            background: 'rgba(217, 119, 6, 0.15)',
                            padding: '1rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(217, 119, 6, 0.3)'
                        }}>
                            <Cpu size={32} color="#f59e0b" />
                        </div>
                        <div>
                            <h3>3. Model Processing</h3>
                            <p className="p-text" style={{ fontSize: '0.95rem' }}>
                                Applies scikit-learn's Random Forest algorithms. We balance positive archaeological sites via a
                                synthetic 1:10 negative sampling ratio based on 3000m buffering logic to minimize false positives.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Step 4 */}
                <div className="card" style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
                        <div style={{
                            background: 'rgba(217, 119, 6, 0.15)',
                            padding: '1rem',
                            borderRadius: '12px',
                            border: '1px solid rgba(217, 119, 6, 0.3)'
                        }}>
                            <Server size={32} color="#f59e0b" />
                        </div>
                        <div>
                            <h3>4. Artifact Export</h3>
                            <p className="p-text" style={{ fontSize: '0.95rem' }}>
                                Resulting probabilistic spatial coordinates are exported as GeoTIFF files using Rasterio and griddata interpolations.
                                Servable instantly to GIS platforms or this React Web Client.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
};

export default ArchitectureTab;
