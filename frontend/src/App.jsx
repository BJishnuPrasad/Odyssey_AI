import React, { useState, useEffect } from 'react';
import { Compass, Map, Brain, Activity, Hexagon } from 'lucide-react';

import HomeTab from './components/HomeTab';
import MapTab from './components/MapTab';
import MLTab from './components/MLTab';
import ArchitectureTab from './components/ArchitectureTab';

function App() {
  const [activeTab, setActiveTab] = useState('home');

  useEffect(() => {
    const handleSwitch = (e) => setActiveTab(e.detail);
    window.addEventListener('switch-tab', handleSwitch);
    return () => window.removeEventListener('switch-tab', handleSwitch);
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case 'home':
        return <HomeTab />;
      case 'map':
        return <MapTab />;
      case 'ml':
        return <MLTab />;
      case 'architecture':
        return <ArchitectureTab />;
      default:
        return <HomeTab />;
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-container">
          <Hexagon className="logo-icon" size={32} strokeWidth={2.5} />
          <h1 className="logo-text">Odyssey AI</h1>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
          >
            <Compass size={18} />
            Overview
          </button>

          <button
            className={`nav-tab ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            <Map size={18} />
            Interactive Map
          </button>

          <button
            className={`nav-tab ${activeTab === 'ml' ? 'active' : ''}`}
            onClick={() => setActiveTab('ml')}
          >
            <Brain size={18} />
            Machine Learning
          </button>

          <button
            className={`nav-tab ${activeTab === 'architecture' ? 'active' : ''}`}
            onClick={() => setActiveTab('architecture')}
          >
            <Activity size={18} />
            Architecture
          </button>
        </nav>
      </header>

      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
