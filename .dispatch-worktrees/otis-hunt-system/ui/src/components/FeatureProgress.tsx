import React, { useState } from 'react';
import { Feature } from '../stores/buildStore';

interface FeatureProgressProps {
  features: Feature[];
  onFeatureClick?: (featureId: string) => void;
}

export const FeatureProgress: React.FC<FeatureProgressProps> = ({
  features,
  onFeatureClick,
}) => {
  const [expandedFeatures, setExpandedFeatures] = useState<Set<string>>(new Set());

  const toggleFeature = (featureId: string) => {
    const newExpanded = new Set(expandedFeatures);
    if (newExpanded.has(featureId)) {
      newExpanded.delete(featureId);
    } else {
      newExpanded.add(featureId);
    }
    setExpandedFeatures(newExpanded);
  };

  const getPriorityColor = (priority: Feature['priority']): string => {
    const colors: Record<string, string> = {
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#10b981',
    };
    return colors[priority] || '#94a3b8';
  };

  const getStatusColor = (status: Feature['status']): string => {
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
    <div className="feature-progress-list">
      {features.map((feature) => {
        const isExpanded = expandedFeatures.has(feature.id);
        const completedTasks = feature.tasks.filter((t) => t.completed).length;

        return (
          <div key={feature.id} className={`feature-progress-item ${feature.status}`}>
            <div
              className="feature-progress-header"
              onClick={() => {
                toggleFeature(feature.id);
                onFeatureClick?.(feature.id);
              }}
            >
              <div className="feature-header-top">
                <span className="feature-name">{feature.name}</span>
                <span
                  className="feature-priority"
                  style={{ color: getPriorityColor(feature.priority) }}
                >
                  {feature.priority}
                </span>
              </div>
              <div className="feature-progress-bar">
                <div
                  className="feature-progress-fill"
                  style={{
                    width: `${feature.progress}%`,
                    backgroundColor: getStatusColor(feature.status),
                  }}
                />
              </div>
              <div className="feature-progress-meta">
                <span>{completedTasks}/{feature.tasks.length} tasks</span>
                <span>{Math.round(feature.progress)}%</span>
              </div>
            </div>

            {isExpanded && (
              <div className="feature-tasks">
                {feature.tasks.map((task) => (
                  <div key={task.id} className={`feature-task ${task.completed ? 'completed' : ''}`}>
                    <input
                      type="checkbox"
                      checked={task.completed}
                      readOnly
                    />
                    <span>{task.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
