import React, { useState, useEffect } from 'react';
import { Pickaxe, Scroll, Search, MapPin, Send } from 'lucide-react';

const HomeTab = () => {
    const [query, setQuery] = useState('');
    const [responseMsg, setResponseMsg] = useState('');

    // We can also have an event system to switch tabs
    const handleSwitchTab = (tabName) => {
        const event = new CustomEvent('switch-tab', { detail: tabName });
        window.dispatchEvent(event);
    };

    const handleQuerySubmit = async (e) => {
        e.preventDefault();
        if (!query) return;

        try {
            const res = await fetch('http://localhost:8000/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            setResponseMsg(data.message);
            setQuery('');
        } catch (error) {
            setResponseMsg("Error connecting to backend API (FastAPI). Ensure you run `python app.py` (or uvicorn app:app).");
        }
    };

    return (
        <div className="content-pane">
            <div style={{ textAlign: 'center', margin: '3rem 0 4rem 0' }}>
                <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>
                    Discovering the Past with <span className="text-gradient">Machine Intelligence</span>
                </h1>
                <p className="p-text" style={{ maxWidth: '800px', margin: '0 auto', fontSize: '1.2rem' }}>
                    Odyssey AI leverages spatial analysis, remote sensing, and advanced machine learning to identify
                    the most probable locations of undiscovered archaeological sites in Thanjavur, Tamil Nadu.
                </p>

                <form onSubmit={handleQuerySubmit} style={{ maxWidth: '600px', margin: '2rem auto 0 auto', display: 'flex', gap: '8px' }}>
                    <input
                        type="text"
                        placeholder="Enter research query (e.g. 'Run analysis on Kaveri delta...')"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        style={{
                            flex: 1, padding: '0.75rem 1rem', borderRadius: '8px',
                            border: '1px solid #334155', background: 'rgba(30, 41, 59, 1)', color: '#f8fafc',
                            fontSize: '1rem', outline: 'none'
                        }}
                    />
                    <button type="submit" className="btn-primary" style={{ padding: '0.75rem 1.2rem' }}>
                        <Send size={18} /> Ask AI
                    </button>
                </form>
                {responseMsg && (
                    <div style={{ color: '#fcd34d', margin: '1rem auto', padding: '1rem', background: 'rgba(217,119,6,0.1)', borderRadius: '8px', display: 'inline-block' }}>
                        {responseMsg}
                    </div>
                )}

                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '2rem' }}>
                    <button className="btn-secondary" onClick={() => handleSwitchTab('map')}>
                        <Search size={20} />
                        Explore Suitability Map
                    </button>
                    <button className="btn-secondary" onClick={() => handleSwitchTab('ml')}>
                        <Scroll size={20} />
                        View ML Models
                    </button>
                </div>
            </div>

            <div className="grid-3" style={{ marginTop: '2rem' }}>
                <div className="card">
                    <div className="card-title">
                        <Scroll className="logo-icon" size={24} />
                        Deep Rich History
                    </div>
                    <p className="p-text">
                        Thanjavur, known as the Rice Bowl of Tamil Nadu, has been a cultural and political hub for millennia.
                        Home to UNESCO World Heritage Sites, its soil holds countless untold stories of the Chola Dynasty and beyond.
                    </p>
                </div>

                <div className="card">
                    <div className="card-title">
                        <MapPin className="logo-icon" size={24} />
                        Geospatial Synthesis
                    </div>
                    <p className="p-text">
                        By fusing Digital Elevation Models (DEM), multi-spectral satellite imagery, distance-to-waterways,
                        and road networks, we reconstruct the fundamental building blocks of ancient settlement logic.
                    </p>
                </div>

                <div className="card">
                    <div className="card-title">
                        <Pickaxe className="logo-icon" size={24} />
                        Predictive Discovery
                    </div>
                    <p className="p-text">
                        Rather than relying solely on surface surveys, our Random Forest framework identifies probabilistic
                        hotspots mapped directly to spatial grids, significantly narrowing down the search areas for excavation.
                    </p>
                </div>
            </div>

            <div className="card" style={{ marginTop: '3rem' }}>
                <h2 className="card-title" style={{ justifyContent: 'center', fontSize: '2rem', borderBottom: 'none' }}>Project Scale</h2>
                <div className="grid-3">
                    <div className="stat-card">
                        <div className="stat-value">3,396</div>
                        <div className="stat-label">Square Kilometers Analyzed</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">240K+</div>
                        <div className="stat-label">Grid Points Processed</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">6+</div>
                        <div className="stat-label">Spatial Meta-Features</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HomeTab;
