import React from 'react';
import { Handle, Position } from 'reactflow';
import { Component } from '../../stores/buildStore';

interface ComponentNodeProps {
  data: {
    component: Component;
    isActive: boolean;
  };
}

export const ComponentNode: React.FC<ComponentNodeProps> = ({ data }) => {
  const { component, isActive } = data;

  const getStatusColor = (): string => {
    const colors: Record<string, string> = {
      not_started: '#475569',
      in_progress: '#3b82f6',
      completed: '#10b981',
      error: '#ef4444',
      blocked: '#f59e0b',
    };
    return colors[component.status] || '#475569';
  };

  const getTypeIcon = (): string => {
    const icons: Record<string, string> = {
      frontend: '🎨',
      backend: '⚙️',
      database: '🗄️',
      service: '🔧',
      api: '🔌',
    };
    return icons[component.type] || '📦';
  };

  return (
    <div
      className={`component-node ${isActive ? 'active' : ''} ${component.status}`}
      style={{ borderColor: getStatusColor() }}
    >
      <Handle type="target" position={Position.Top} />
      
      <div className="node-header">
        <span className="node-icon">{getTypeIcon()}</span>
        <span className="node-type">{component.type}</span>
      </div>

      <div className="node-body">
        <h3>{component.name}</h3>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ 
              width: `${component.progress}%`,
              backgroundColor: getStatusColor(),
            }}
          />
        </div>
        <span className="progress-text">{Math.round(component.progress)}%</span>
      </div>

      {component.error && (
        <div className="node-error">
          <span>⚠️</span>
          <span>{component.error}</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
