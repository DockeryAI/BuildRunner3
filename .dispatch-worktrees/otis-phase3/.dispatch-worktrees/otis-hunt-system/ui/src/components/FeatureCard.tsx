/**
 * FeatureCard Component
 * Expandable card for displaying and editing PRD features
 * Supports drag-and-drop reordering
 */

import React, { useState, useEffect } from 'react';
import './FeatureCard.css';

export interface Feature {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  status?: 'implemented' | 'partial' | 'planned';
  acceptance_criteria?: string;
  version?: string; // e.g., "1.0.0", "1.1.0", "2.0.0"
  group?: string; // Feature group for organization (e.g., "MVP Features", "Phase 2")
}

interface FeatureCardProps {
  feature: Feature;
  onUpdate: (feature: Feature) => void;
  onDelete: (id: string) => void;
  onMoveToVersion?: (feature: Feature, targetVersion: string) => void;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
  onDragEnd?: (e: React.DragEvent) => void;
}

export function FeatureCard({
  feature,
  onUpdate,
  onDelete,
  onMoveToVersion,
  draggable = true,
  onDragStart,
  onDragEnd,
}: FeatureCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedFeature, setEditedFeature] = useState<Feature>(feature);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });

  const priorityEmoji = {
    high: '🔴',
    medium: '🟡',
    low: '🟢',
  }[feature.priority];

  const priorityClass = {
    high: 'priority-high',
    medium: 'priority-medium',
    low: 'priority-low',
  }[feature.priority];

  const statusEmoji = {
    implemented: '✅',
    partial: '🟡',
    planned: '📋',
  }[feature.status || 'planned'];

  const statusLabel = {
    implemented: 'Implemented',
    partial: 'In Progress',
    planned: 'Planned',
  }[feature.status || 'planned'];

  const handleSave = () => {
    onUpdate(editedFeature);
    setEditing(false);
  };

  const handleCancel = () => {
    setEditedFeature(feature);
    setEditing(false);
  };

  const handleDelete = () => {
    if (confirm(`Delete feature "${feature.title}"?`)) {
      onDelete(feature.id);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenuPos({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleMoveToVersion = (version: string | undefined) => {
    const updatedFeature = { ...feature, version };
    onUpdate(updatedFeature);
    setShowContextMenu(false);
  };

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setShowContextMenu(false);
    if (showContextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showContextMenu]);

  return (
    <>
      <div
        className={`feature-card ${expanded ? 'expanded' : ''} ${priorityClass}`}
        draggable={draggable && !editing}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onContextMenu={handleContextMenu}
      >
      <div className="feature-card-header" onClick={() => !editing && setExpanded(!expanded)}>
        {draggable && <div className="drag-handle">☰</div>}
        <div className="priority-badge">{priorityEmoji}</div>
        <div className="feature-info">
          <div className="feature-title">
            {editing ? (
              <input
                type="text"
                className="title-input"
                value={editedFeature.title}
                onChange={(e) => setEditedFeature({ ...editedFeature, title: e.target.value })}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span>
                {feature.title}
                <span className="status-badge-header" title={statusLabel}>
                  {statusEmoji}
                </span>
                {feature.version && (
                  <span className="version-badge-header" title={`Scheduled for v${feature.version}`}>
                    v{feature.version}
                  </span>
                )}
              </span>
            )}
          </div>
          {!expanded && !editing && (
            <div className="feature-description-preview">
              {feature.description}
            </div>
          )}
        </div>
        <div className="card-actions">
          {!editing && (
            <>
              <button
                className="action-btn edit-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  setEditing(true);
                  setExpanded(true);
                }}
                title="Edit feature"
              >
                ✏️
              </button>
              <button
                className="action-btn delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete();
                }}
                title="Delete feature"
              >
                🗑️
              </button>
            </>
          )}
          <button className="expand-btn" onClick={() => setExpanded(!expanded)}>
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="feature-card-body">
          <div className="field-group">
            <label>Description</label>
            {editing ? (
              <textarea
                className="description-input"
                value={editedFeature.description}
                onChange={(e) =>
                  setEditedFeature({ ...editedFeature, description: e.target.value })
                }
                rows={3}
              />
            ) : (
              <p className="description-text">{feature.description}</p>
            )}
          </div>

          <div className="field-group">
            <label>Priority</label>
            {editing ? (
              <select
                className="priority-select"
                value={editedFeature.priority}
                onChange={(e) =>
                  setEditedFeature({
                    ...editedFeature,
                    priority: e.target.value as 'high' | 'medium' | 'low',
                  })
                }
              >
                <option value="high">🔴 High</option>
                <option value="medium">🟡 Medium</option>
                <option value="low">🟢 Low</option>
              </select>
            ) : (
              <span className="priority-text">
                {priorityEmoji} {feature.priority.charAt(0).toUpperCase() + feature.priority.slice(1)}
              </span>
            )}
          </div>

          <div className="field-group">
            <label>Status</label>
            {editing ? (
              <select
                className="status-select"
                value={editedFeature.status || 'planned'}
                onChange={(e) =>
                  setEditedFeature({
                    ...editedFeature,
                    status: e.target.value as 'implemented' | 'partial' | 'planned',
                  })
                }
              >
                <option value="implemented">✅ Implemented</option>
                <option value="partial">🟡 In Progress</option>
                <option value="planned">📋 Planned</option>
              </select>
            ) : (
              <span className="status-text">
                {statusEmoji} {statusLabel}
              </span>
            )}
          </div>

          <div className="field-group">
            <label>Acceptance Criteria</label>
            {editing ? (
              <textarea
                className="criteria-input"
                value={editedFeature.acceptance_criteria || ''}
                onChange={(e) =>
                  setEditedFeature({ ...editedFeature, acceptance_criteria: e.target.value })
                }
                placeholder="- [ ] Criterion 1&#10;- [ ] Criterion 2&#10;- [ ] Criterion 3"
                rows={4}
              />
            ) : (
              <div className="criteria-text">
                {feature.acceptance_criteria || 'No acceptance criteria defined'}
              </div>
            )}
          </div>

          <div className="field-group">
            <label>Target Version</label>
            {editing ? (
              <select
                className="version-select"
                value={editedFeature.version || 'current'}
                onChange={(e) =>
                  setEditedFeature({
                    ...editedFeature,
                    version: e.target.value === 'current' ? undefined : e.target.value,
                  })
                }
              >
                <option value="current">Current Version</option>
                <option value="1.1.0">v1.1.0 (Patch)</option>
                <option value="1.2.0">v1.2.0 (Minor)</option>
                <option value="2.0.0">v2.0.0 (Major)</option>
              </select>
            ) : (
              <span className="version-badge">
                {feature.version ? `v${feature.version}` : 'Current'}
              </span>
            )}
          </div>

          {editing && (
            <div className="edit-actions">
              <button className="save-btn" onClick={handleSave}>
                💾 Save
              </button>
              <button className="cancel-btn" onClick={handleCancel}>
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>

      {/* Context Menu */}
      {showContextMenu && (
        <div
          className="context-menu"
          style={{
            position: 'fixed',
            top: contextMenuPos.y,
            left: contextMenuPos.x,
            zIndex: 1000,
          }}
        >
          <div className="context-menu-header">Move to Version</div>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion(undefined)}
          >
            Current (No Version)
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('1.1.0')}
          >
            v1.1.0 (Patch)
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('1.2.0')}
          >
            v1.2.0 (Minor)
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('2.0.0')}
          >
            v2.0.0 (Major)
          </button>
        </div>
      )}
    </>
  );
}
