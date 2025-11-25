import React from 'react';
import { Component } from '../stores/buildStore';

interface ComponentProgressProps {
  components: Component[];
  onComponentClick?: (componentId: string) => void;
}

export const ComponentProgress: React.FC<ComponentProgressProps> = ({
  components,
  onComponentClick,
}) => {
  const getStatusColor = (status: Component['status']): string => {
    const colors: Record<string, string> = {
      not_started: '#475569',
      in_progress: '#3b82f6',
      completed: '#10b981',
      error: '#ef4444',
      blocked: '#f59e0b',
    };
    return colors[status] || '#475569';
  };

  return (
    <div className="component-progress-list">
      {components.map((comp) => (
        <div
          key={comp.id}
          className={`component-progress-item ${comp.status}`}
          onClick={() => onComponentClick?.(comp.id)}
        >
          <div className="component-progress-header">
            <span className="component-name">{comp.name}</span>
            <span className="component-status">{comp.status.replace('_', ' ')}</span>
          </div>
          <div className="component-progress-bar">
            <div
              className="component-progress-fill"
              style={{
                width: `${comp.progress}%`,
                backgroundColor: getStatusColor(comp.status),
              }}
            />
          </div>
          <div className="component-progress-details">
            <span>{Math.round(comp.progress)}%</span>
            <span>{comp.files.length} files</span>
            <span className={comp.testsPass ? 'tests-pass' : 'tests-fail'}>
              {comp.testsPass ? '✓' : '✗'} Tests
            </span>
          </div>
          {comp.error && (
            <div className="component-error-msg">{comp.error}</div>
          )}
        </div>
      ))}
    </div>
  );
};
