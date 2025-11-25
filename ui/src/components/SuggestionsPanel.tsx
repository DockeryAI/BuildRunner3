/**
 * SuggestionsPanel Component
 * AI-powered suggestions sidebar with on-demand generation
 * Drag suggestions into PRD or dismiss them
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './SuggestionsPanel.css';

const API_URL = 'http://localhost:8080';

export interface Suggestion {
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  rationale: string;
  subsection?: string;
}

interface SuggestionsPanelProps {
  projectContext: {
    overview: any;
    features: any[];
  };
  section: string;
  subsection?: string;
  onAddSuggestion: (suggestion: Suggestion) => void;
  usedSuggestions: Set<string>;
  onRestoreSuggestions: () => void;
  getSuggestionKey: (suggestion: Suggestion) => string;
}

interface SuggestionCardProps {
  suggestion: Suggestion;
  index: number;
  onAddSuggestion: (suggestion: Suggestion, version?: string) => void;
  onDismiss: (index: number) => void;
  onDragStart: (e: React.DragEvent, suggestion: Suggestion) => void;
}

function SuggestionCard({ suggestion, index, onAddSuggestion, onDismiss, onDragStart }: SuggestionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setShowContextMenu(false);
    if (showContextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showContextMenu]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenuPos({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleMoveToVersion = (version: string) => {
    setShowContextMenu(false);
    onAddSuggestion(suggestion, version);
  };

  const priorityEmoji = (priority: string) => {
    return { high: '🔴', medium: '🟡', low: '🟢' }[priority] || '🟡';
  };

  const getSubsectionClass = (subsection?: string) => {
    const mapping: Record<string, string> = {
      'name': 'subsection-tag-name',
      'summary': 'subsection-tag-summary',
      'goals': 'subsection-tag-goals',
      'users': 'subsection-tag-users'
    };
    return subsection ? mapping[subsection] || '' : '';
  };

  const getSubsectionLabel = (subsection?: string) => {
    const labels: Record<string, string> = {
      'name': 'Project Name',
      'summary': 'Executive Summary',
      'goals': 'Goals',
      'users': 'Target Users'
    };
    return subsection ? labels[subsection] || subsection : null;
  };

  return (
    <div
      className={`suggestion-card ${expanded ? 'expanded' : ''}`}
      draggable
      onDragStart={(e) => onDragStart(e, suggestion)}
      onContextMenu={handleContextMenu}
    >
      <div className="suggestion-header" onClick={() => setExpanded(!expanded)}>
        <span className="suggestion-priority">{priorityEmoji(suggestion.priority)}</span>
        <div className="suggestion-info">
          {suggestion.subsection && (
            <span className={`subsection-tag ${getSubsectionClass(suggestion.subsection)}`}>
              {getSubsectionLabel(suggestion.subsection)}
            </span>
          )}
          <h4 className="suggestion-title">{suggestion.title}</h4>
          {!expanded && (
            <p className="suggestion-description-preview">{suggestion.description}</p>
          )}
        </div>
        <div className="suggestion-header-actions">
          <button
            className="dismiss-btn"
            onClick={(e) => {
              e.stopPropagation();
              onDismiss(index);
            }}
            title="Dismiss suggestion"
          >
            ✕
          </button>
          <button className="expand-btn-suggestion" onClick={() => setExpanded(!expanded)}>
            {expanded ? '▼' : '▶'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="suggestion-body">
          <p className="suggestion-description">{suggestion.description}</p>

          {suggestion.rationale && (
            <div className="suggestion-rationale">
              <strong>Why:</strong> {suggestion.rationale}
            </div>
          )}

          <div className="suggestion-actions">
            <button
              className="add-btn"
              onClick={() => onAddSuggestion(suggestion)}
            >
              ➕ Add to PRD
            </button>
            <span className="drag-hint">or drag to add</span>
          </div>
        </div>
      )}

      {/* Context Menu */}
      {showContextMenu && (
        <div
          className="context-menu"
          style={{
            position: 'fixed',
            top: `${contextMenuPos.y}px`,
            left: `${contextMenuPos.x}px`,
            zIndex: 1000,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="context-menu-header">Move to Version</div>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('current')}
          >
            📌 Current Version
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('v1.1.0')}
          >
            🔖 v1.1.0
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('v1.2.0')}
          >
            🔖 v1.2.0
          </button>
          <button
            className="context-menu-item"
            onClick={() => handleMoveToVersion('v2.0.0')}
          >
            🔖 v2.0.0
          </button>
        </div>
      )}
    </div>
  );
}

export function SuggestionsPanel({
  projectContext,
  section,
  subsection,
  onAddSuggestion,
  usedSuggestions,
  onRestoreSuggestions,
  getSuggestionKey,
}: SuggestionsPanelProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customRequest, setCustomRequest] = useState('');
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Auto-load suggestions when component mounts or section/subsection changes
  useEffect(() => {
    if (projectContext.overview || section === 'features') {
      generateSuggestions();
    }
  }, [section, subsection]); // Re-generate when section or subsection changes

  const generateSuggestions = async (customReq?: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_URL}/api/prd/suggestions`, {
        project_context: projectContext,
        section: section,
        subsection: subsection || null,
        custom_request: customReq || null,
      });

      if (response.data.success) {
        setSuggestions(response.data.suggestions);
        setDismissedIds(new Set()); // Reset dismissed on new generation
      } else {
        setError(response.data.error || 'Failed to generate suggestions');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate suggestions');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomRequest = () => {
    if (customRequest.trim()) {
      generateSuggestions(customRequest);
      setCustomRequest('');
    }
  };

  const handleDismiss = (index: number) => {
    const newDismissed = new Set(dismissedIds);
    newDismissed.add(index.toString());
    setDismissedIds(newDismissed);
  };

  const handleDragStart = (e: React.DragEvent, suggestion: Suggestion) => {
    e.dataTransfer.setData('application/json', JSON.stringify(suggestion));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const visibleSuggestions = suggestions.filter(
    (suggestion, index) => {
      const isDismissed = dismissedIds.has(index.toString());
      const isUsed = usedSuggestions.has(getSuggestionKey(suggestion));
      return !isDismissed && !isUsed;
    }
  );

  return (
    <div className="suggestions-panel">
      <div className="panel-header">
        <h3>💡 AI Suggestions</h3>
        <span className="section-tag">
          {section === 'overview' && subsection ? `${subsection}` : section}
        </span>
      </div>

      <div className="panel-controls">
        <button
          className="generate-btn"
          onClick={() => generateSuggestions()}
          disabled={loading}
        >
          {loading ? '⏳ Generating...' : '✨ Generate Suggestions'}
        </button>

        <div className="custom-request">
          <input
            type="text"
            className="request-input"
            placeholder="Ask for specific suggestions..."
            value={customRequest}
            onChange={(e) => setCustomRequest(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCustomRequest()}
            disabled={loading}
          />
          <button
            className="request-btn"
            onClick={handleCustomRequest}
            disabled={loading || !customRequest.trim()}
          >
            Ask
          </button>
        </div>
      </div>

      {error && (
        <div className="error-box">
          <span>❌ {error}</span>
        </div>
      )}

      <div className="suggestions-list">
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>AI is thinking...</p>
          </div>
        )}

        {!loading && visibleSuggestions.length === 0 && !error && (
          <div className="empty-state">
            <p>Click "Generate Suggestions" to get AI-powered ideas for your PRD.</p>
            <p className="hint">💡 Try asking for specific suggestions using the text box above.</p>
          </div>
        )}

        {!loading &&
          visibleSuggestions.map((suggestion, index) => (
            <SuggestionCard
              key={index}
              suggestion={suggestion}
              index={index}
              onAddSuggestion={onAddSuggestion}
              onDismiss={handleDismiss}
              onDragStart={handleDragStart}
            />
          ))}
      </div>

      {visibleSuggestions.length > 0 && !loading && (
        <div className="panel-footer">
          <span className="count">
            {visibleSuggestions.length} suggestion{visibleSuggestions.length !== 1 ? 's' : ''}
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {usedSuggestions.size > 0 && (
              <button
                className="restore-btn"
                onClick={onRestoreSuggestions}
                title="Restore hidden suggestions"
              >
                ↺ Restore
              </button>
            )}
            <button className="refresh-btn" onClick={() => generateSuggestions()}>
              🔄 Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
