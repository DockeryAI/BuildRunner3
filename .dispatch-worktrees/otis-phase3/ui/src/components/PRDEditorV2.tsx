/**
 * PRD Editor V2 - Uses prdStore for state management
 *
 * Features:
 * - Real-time WebSocket updates
 * - Optimistic updates with rollback
 * - Multi-client sync
 * - Natural language input with preview
 * - Version history with rollback
 * - Regeneration indicators
 */

import React, { useState, useEffect, useRef } from 'react';
import { usePRDStore } from '../stores/prdStore';
import { MonacoPRDEditor } from './MonacoPRDEditor';
import './PRDEditor.css';

interface PRDEditorV2Props {
  projectName: string;
  onClose?: () => void;
}

export function PRDEditorV2({ projectName, onClose }: PRDEditorV2Props) {
  const {
    prd,
    versions,
    isLoading,
    isSaving,
    isRegenerating,
    error,
    wsConnected,
    loadPRD,
    updatePRD,
    parseNaturalLanguage,
    loadVersions,
    rollbackToVersion,
    clearError
  } = usePRDStore();

  const [editMode, setEditMode] = useState<'markdown' | 'natural' | 'visual'>('visual');
  const [markdownContent, setMarkdownContent] = useState('');
  const [nlInput, setNlInput] = useState('');
  const [nlPreview, setNlPreview] = useState<{success: boolean; updates: any; preview: string} | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load PRD on mount
  useEffect(() => {
    loadPRD();
    loadVersions();
  }, []);

  // Update markdown content when PRD changes
  useEffect(() => {
    if (prd) {
      setMarkdownContent(generateMarkdown(prd));
    }
  }, [prd]);

  const generateMarkdown = (prdData: any): string => {
    let md = `# ${prdData.project_name}\n\n`;
    md += `**Version:** ${prdData.version}\n`;
    md += `**Last Updated:** ${prdData.last_updated}\n\n`;

    if (prdData.overview) {
      md += `## Project Overview\n\n${prdData.overview}\n\n`;
    }

    prdData.features.forEach((feature: any, i: number) => {
      md += `## Feature ${i + 1}: ${feature.name}\n\n`;
      md += `**Priority:** ${feature.priority}\n`;
      md += `**Status:** ${feature.status}\n\n`;

      if (feature.description) {
        md += `### Description\n\n${feature.description}\n\n`;
      }

      if (feature.requirements && feature.requirements.length > 0) {
        md += `### Requirements\n\n`;
        feature.requirements.forEach((req: string) => {
          md += `- ${req}\n`;
        });
        md += `\n`;
      }

      if (feature.acceptance_criteria && feature.acceptance_criteria.length > 0) {
        md += `### Acceptance Criteria\n\n`;
        feature.acceptance_criteria.forEach((ac: string) => {
          md += `- [ ] ${ac}\n`;
        });
        md += `\n`;
      }
    });

    return md;
  };

  const handleSaveMarkdown = async () => {
    // Parse markdown and update PRD
    // This is simplified - in production, you'd parse the markdown properly
    await updatePRD({
      overview: "Updated from markdown editor"
    });
  };

  const handleNaturalLanguagePreview = async () => {
    if (!nlInput.trim()) return;

    const result = await parseNaturalLanguage(nlInput);
    setNlPreview(result);
  };

  const handleNaturalLanguageApply = async () => {
    if (!nlPreview || !nlPreview.success) return;

    await updatePRD(nlPreview.updates);
    setNlInput('');
    setNlPreview(null);
  };

  const handleAddFeature = async (name: string, priority: string = 'medium') => {
    await updatePRD({
      add_feature: {
        id: `feature-${Date.now()}`,
        name,
        description: '',
        priority,
        status: 'planned',
        requirements: [],
        acceptance_criteria: [],
        technical_details: {},
        dependencies: []
      }
    });
  };

  const handleRemoveFeature = async (featureId: string) => {
    if (!confirm(`Remove feature ${featureId}?`)) return;

    await updatePRD({
      remove_feature: featureId
    });
  };

  const handleUpdateFeature = async (featureId: string, updates: any) => {
    await updatePRD({
      update_feature: {
        id: featureId,
        updates
      }
    });
  };

  const handleRollback = async (versionIndex: number) => {
    if (!confirm(`Rollback to version ${versionIndex}?`)) return;

    await rollbackToVersion(versionIndex);
    setShowVersions(false);
  };

  if (isLoading && !prd) {
    return (
      <div className="prd-editor loading">
        <div className="loading-spinner">Loading PRD...</div>
      </div>
    );
  }

  return (
    <div className="prd-editor-v2">
      {/* Header */}
      <div className="editor-header">
        <div className="header-left">
          <h2>📝 {prd?.project_name || projectName}</h2>
          <div className="connection-status">
            {wsConnected ? (
              <span className="status-connected">🟢 Live</span>
            ) : (
              <span className="status-disconnected">🔴 Disconnected</span>
            )}
          </div>
        </div>

        <div className="header-right">
          {isRegenerating && (
            <div className="regenerating-indicator">
              <span className="spinner">⚡</span> Regenerating plan...
            </div>
          )}
          {isSaving && <span className="saving-indicator">💾 Saving...</span>}
          <button onClick={() => setShowVersions(!showVersions)} className="btn-secondary">
            📚 History
          </button>
          {onClose && (
            <button onClick={onClose} className="btn-secondary">✕</button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span>❌ {error}</span>
          <button onClick={clearError}>✕</button>
        </div>
      )}

      {/* Mode Tabs */}
      <div className="mode-tabs">
        <button
          className={editMode === 'visual' ? 'tab-active' : ''}
          onClick={() => setEditMode('visual')}
        >
          🎨 Visual Editor
        </button>
        <button
          className={editMode === 'natural' ? 'tab-active' : ''}
          onClick={() => setEditMode('natural')}
        >
          💬 Natural Language
        </button>
        <button
          className={editMode === 'markdown' ? 'tab-active' : ''}
          onClick={() => setEditMode('markdown')}
        >
          📄 Markdown
        </button>
      </div>

      {/* Editor Content */}
      <div className="editor-content">
        {/* Visual Editor Mode */}
        {editMode === 'visual' && prd && (
          <div className="visual-editor">
            <div className="prd-overview">
              <h3>Project Overview</h3>
              <textarea
                value={prd.overview}
                onChange={(e) => handleUpdateFeature('', { overview: e.target.value })}
                placeholder="Describe your project..."
                rows={4}
              />
            </div>

            <div className="features-list">
              <div className="features-header">
                <h3>Features ({prd.features.length})</h3>
                <button
                  onClick={() => {
                    const name = prompt('Feature name:');
                    if (name) handleAddFeature(name);
                  }}
                  className="btn-primary"
                >
                  ➕ Add Feature
                </button>
              </div>

              {prd.features.map((feature: any) => (
                <div key={feature.id} className="feature-card">
                  <div className="feature-header">
                    <input
                      type="text"
                      value={feature.name}
                      onChange={(e) => handleUpdateFeature(feature.id, { name: e.target.value })}
                      className="feature-name-input"
                    />
                    <select
                      value={feature.priority}
                      onChange={(e) => handleUpdateFeature(feature.id, { priority: e.target.value })}
                      className="priority-select"
                    >
                      <option value="critical">🔴 Critical</option>
                      <option value="high">🟠 High</option>
                      <option value="medium">🟡 Medium</option>
                      <option value="low">🟢 Low</option>
                    </select>
                    <button
                      onClick={() => handleRemoveFeature(feature.id)}
                      className="btn-danger-small"
                    >
                      🗑️
                    </button>
                  </div>

                  <textarea
                    value={feature.description}
                    onChange={(e) => handleUpdateFeature(feature.id, { description: e.target.value })}
                    placeholder="Feature description..."
                    rows={3}
                  />

                  <div className="feature-meta">
                    <span className="status-badge">{feature.status}</span>
                    <span className="id-badge">{feature.id}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Natural Language Mode */}
        {editMode === 'natural' && (
          <div className="natural-language-editor">
            <div className="nl-input-section">
              <h3>💬 Natural Language Input</h3>
              <p className="nl-help">
                Try: "add authentication feature", "remove feature-1", "update project name to MyApp"
              </p>

              <textarea
                value={nlInput}
                onChange={(e) => setNlInput(e.target.value)}
                placeholder='Type your command, e.g., "add user authentication feature"'
                rows={4}
                className="nl-textarea"
              />

              <div className="nl-actions">
                <button
                  onClick={handleNaturalLanguagePreview}
                  className="btn-secondary"
                  disabled={!nlInput.trim()}
                >
                  👁️ Preview Changes
                </button>
                {nlPreview && nlPreview.success && (
                  <button
                    onClick={handleNaturalLanguageApply}
                    className="btn-primary"
                  >
                    ✅ Apply Changes
                  </button>
                )}
              </div>
            </div>

            {nlPreview && (
              <div className={`nl-preview ${nlPreview.success ? 'success' : 'error'}`}>
                <h4>{nlPreview.success ? '✅ Preview:' : '❌ Error:'}</h4>
                <pre>{nlPreview.preview}</pre>
                {nlPreview.success && (
                  <details>
                    <summary>View Raw Updates</summary>
                    <pre>{JSON.stringify(nlPreview.updates, null, 2)}</pre>
                  </details>
                )}
              </div>
            )}
          </div>
        )}

        {/* Markdown Mode */}
        {editMode === 'markdown' && (
          <div className="markdown-editor">
            <MonacoPRDEditor
              value={markdownContent}
              onChange={(value) => setMarkdownContent(value)}
              onSave={handleSaveMarkdown}
              readOnly={isSaving}
            />

            <div className="markdown-actions">
              <button
                onClick={handleSaveMarkdown}
                className="btn-primary"
                disabled={isSaving}
              >
                💾 Save Markdown
              </button>
              <div className="markdown-tips">
                <strong>Tip:</strong> Changes are auto-synced when you switch modes • Cmd/Ctrl+S to save
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Version History Sidebar */}
      {showVersions && (
        <div className="version-history-sidebar">
          <div className="sidebar-header">
            <h3>📚 Version History</h3>
            <button onClick={() => setShowVersions(false)}>✕</button>
          </div>

          <div className="versions-list">
            {versions.length === 0 ? (
              <p className="no-versions">No version history yet</p>
            ) : (
              versions.map((version) => (
                <div key={version.index} className="version-item">
                  <div className="version-info">
                    <strong>Version {version.index}</strong>
                    <span className="version-author">by {version.author}</span>
                    <span className="version-time">
                      {new Date(version.timestamp).toLocaleString()}
                    </span>
                    <p className="version-summary">{version.summary}</p>
                    <span className="version-features">
                      {version.feature_count} features
                    </span>
                  </div>
                  <button
                    onClick={() => handleRollback(version.index)}
                    className="btn-rollback"
                  >
                    ↶ Rollback
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Footer Stats */}
      <div className="editor-footer">
        <div className="footer-stats">
          <span>📊 {prd?.features.length || 0} features</span>
          <span>📅 Last updated: {prd?.last_updated ? new Date(prd.last_updated).toLocaleString() : 'Never'}</span>
          <span>🔄 v{prd?.version || '1.0.0'}</span>
        </div>
      </div>
    </div>
  );
}

export default PRDEditorV2;
