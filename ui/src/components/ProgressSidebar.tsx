import React, { useState } from 'react';
import { Component, Feature } from '../stores/buildStore';
import { ComponentProgress } from './ComponentProgress';
import { FeatureProgress } from './FeatureProgress';
import './ProgressSidebar.css';

interface ProgressSidebarProps {
  components: Component[];
  features: Feature[];
}

export const ProgressSidebar: React.FC<ProgressSidebarProps> = ({
  components,
  features,
}) => {
  const [activeTab, setActiveTab] = useState<'components' | 'features'>('components');

  const overallProgress = React.useMemo(() => {
    if (components.length === 0) return 0;
    const total = components.reduce((sum, comp) => sum + comp.progress, 0);
    return Math.round(total / components.length);
  }, [components]);

  return (
    <div className="progress-sidebar">
      <div className="progress-sidebar-header">
        <h2>Build Progress</h2>
        <div className="overall-progress">
          <div className="overall-progress-bar">
            <div 
              className="overall-progress-fill"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          <span className="overall-progress-text">{overallProgress}%</span>
        </div>
      </div>

      <div className="progress-tabs">
        <button
          className={`progress-tab ${activeTab === 'components' ? 'active' : ''}`}
          onClick={() => setActiveTab('components')}
        >
          Components ({components.length})
        </button>
        <button
          className={`progress-tab ${activeTab === 'features' ? 'active' : ''}`}
          onClick={() => setActiveTab('features')}
        >
          Features ({features.length})
        </button>
      </div>

      <div className="progress-content">
        {activeTab === 'components' ? (
          <ComponentProgress components={components} />
        ) : (
          <FeatureProgress features={features} />
        )}
      </div>
    </div>
  );
};
