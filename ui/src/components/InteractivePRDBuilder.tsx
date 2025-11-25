/**
 * InteractivePRDBuilder Component
 * Split-panel editor for creating PRDs with AI assistance
 * Left: PRD sections (overview, features, user stories, etc.)
 * Right: AI suggestions panel
 */

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FeatureCard, Feature } from './FeatureCard';
import { SuggestionsPanel, Suggestion } from './SuggestionsPanel';
import { parsePRD, serializePRD } from '../utils/prdParser';
import './InteractivePRDBuilder.css';

const API_URL = 'http://localhost:8080';

interface PRDData {
  project_name: string;
  overview: {
    executive_summary: string;
    goals: string;
    target_users: string;
  };
  features: Feature[];
  user_stories: string[];
  technical_requirements: {
    frontend: string;
    backend: string;
    database: string;
    infrastructure: string;
  };
  success_criteria: string[];
}

interface InteractivePRDBuilderProps {
  projectName: string;
  projectPath: string;
  initialPRD?: Partial<PRDData>;
  onSave?: () => void;
  onCreateProject?: (prdData: PRDData) => void;
}

export function InteractivePRDBuilder({
  projectName,
  projectPath,
  initialPRD,
  onSave,
  onCreateProject,
}: InteractivePRDBuilderProps) {
  const [prdData, setPrdData] = useState<PRDData>({
    project_name: projectName,
    overview: initialPRD?.overview || {
      executive_summary: '',
      goals: '',
      target_users: '',
    },
    features: initialPRD?.features || [],
    user_stories: initialPRD?.user_stories || [],
    technical_requirements: initialPRD?.technical_requirements || {
      frontend: '',
      backend: '',
      database: '',
      infrastructure: '',
    },
    success_criteria: initialPRD?.success_criteria || [],
  });

  const [activeSection, setActiveSection] = useState<string>('overview');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [isResizing, setIsResizing] = useState(false);
  const [suggestionsWidth, setSuggestionsWidth] = useState(400);
  const [isResizingSuggestions, setIsResizingSuggestions] = useState(false);
  const [usedSuggestions, setUsedSuggestions] = useState<Set<string>>(new Set());
  const [versionFilter, setVersionFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [hasInitialized, setHasInitialized] = useState(false);
  const [autoSaveTimeout, setAutoSaveTimeout] = useState<NodeJS.Timeout | null>(null);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [lastFileModified, setLastFileModified] = useState<number | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const fileWatcherRef = useRef<NodeJS.Timeout | null>(null);

  // Helper to generate unique key for suggestions
  const getSuggestionKey = (suggestion: Suggestion) => {
    return `${suggestion.title}|${suggestion.description.substring(0, 50)}`;
  };

  // Watch PROJECT_SPEC.md for changes (polling every 500ms)
  useEffect(() => {
    if (!projectPath) return;

    const watchFile = async () => {
      try {
        const response = await axios.post(`${API_URL}/api/prd/read`, {
          project_path: projectPath,
        });

        if (response.data.success && response.data.prd_markdown) {
          const fileModTime = response.data.last_modified || Date.now();

          // Only parse if file has changed
          if (lastFileModified === null || fileModTime > lastFileModified) {
            setLastFileModified(fileModTime);

            // Don't parse if we're currently saving (avoid circular updates)
            if (!saving && !isParsing) {
              setIsParsing(true);
              const parsed = parsePRD(response.data.prd_markdown);

              // Only update if content actually changed
              const currentJson = JSON.stringify(prdData);
              const parsedJson = JSON.stringify(parsed);

              if (currentJson !== parsedJson) {
                setPrdData(parsed);
              }

              setIsParsing(false);
            }
          }
        }
      } catch (err) {
        console.error('File watcher error:', err);
      }
    };

    // Initial load
    watchFile();

    // Poll every 500ms
    fileWatcherRef.current = setInterval(watchFile, 500);

    return () => {
      if (fileWatcherRef.current) {
        clearInterval(fileWatcherRef.current);
      }
    };
  }, [projectPath, lastFileModified, saving, isParsing]);

  // Auto-generate feature IDs
  useEffect(() => {
    setPrdData((prev) => ({
      ...prev,
      features: prev.features.map((f, i) =>
        f.id ? f : { ...f, id: `feature-${Date.now()}-${i}` }
      ),
    }));
    // Mark as initialized after first render
    setHasInitialized(true);
  }, []);

  // Auto-save PRD changes with debounce (after initialization)
  useEffect(() => {
    if (!hasInitialized) return;

    // Mark as unsaved when data changes
    setLastSaved(null);

    // Clear existing timeout
    if (autoSaveTimeout) {
      clearTimeout(autoSaveTimeout);
    }

    // Set new timeout to save after 2 seconds of inactivity
    const timeout = setTimeout(() => {
      handleSavePRD();
    }, 2000);

    setAutoSaveTimeout(timeout);

    // Cleanup on unmount
    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [prdData, hasInitialized]);

  // Handle sidebar resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = e.clientX;
        if (newWidth >= 200 && newWidth <= 400) {
          setSidebarWidth(newWidth);
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Handle suggestions panel resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingSuggestions) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth >= 300 && newWidth <= 600) {
          setSuggestionsWidth(newWidth);
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizingSuggestions(false);
    };

    if (isResizingSuggestions) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingSuggestions]);

  const handleAddSuggestion = (suggestion: Suggestion, version?: string) => {
    // Track this suggestion as used
    const suggestionKey = getSuggestionKey(suggestion);
    setUsedSuggestions((prev) => new Set(prev).add(suggestionKey));

    // Handle overview subsection suggestions
    if (suggestion.subsection) {
      setPrdData((prev) => {
        const newData = { ...prev };

        switch (suggestion.subsection) {
          case 'name':
            // For project name, replace with the suggestion title
            newData.project_name = suggestion.title;
            break;

          case 'summary':
            // Append to executive summary
            const currentSummary = (newData.overview?.executive_summary || '').trim();
            newData.overview = {
              ...newData.overview,
              executive_summary: currentSummary
                ? `${currentSummary}\n\n${suggestion.description}`
                : suggestion.description,
              goals: newData.overview?.goals || '',
              target_users: newData.overview?.target_users || ''
            };
            break;

          case 'goals':
            // Append to goals
            const currentGoals = (newData.overview?.goals || '').trim();
            newData.overview = {
              ...newData.overview,
              executive_summary: newData.overview?.executive_summary || '',
              goals: currentGoals
                ? `${currentGoals}\n\n${suggestion.description}`
                : suggestion.description,
              target_users: newData.overview?.target_users || ''
            };
            break;

          case 'users':
            // Append to target users
            const currentUsers = (newData.overview?.target_users || '').trim();
            newData.overview = {
              ...newData.overview,
              executive_summary: newData.overview?.executive_summary || '',
              goals: newData.overview?.goals || '',
              target_users: currentUsers
                ? `${currentUsers}\n\n${suggestion.description}`
                : suggestion.description
            };
            break;
        }

        return newData;
      });
    } else {
      // Handle feature suggestions (default behavior)
      const newFeature: Feature = {
        id: `feature-${Date.now()}`,
        title: suggestion.title,
        description: suggestion.description,
        priority: suggestion.priority,
        acceptance_criteria: `- [ ] To be defined`,
        ...(version && { version }), // Add version if provided
      };
      setPrdData((prev) => ({
        ...prev,
        features: [...prev.features, newFeature],
      }));
    }
  };

  const handleUpdateFeature = (updatedFeature: Feature) => {
    setPrdData((prev) => ({
      ...prev,
      features: prev.features.map((f) => (f.id === updatedFeature.id ? updatedFeature : f)),
    }));
  };

  const handleDeleteFeature = (id: string) => {
    setPrdData((prev) => ({
      ...prev,
      features: prev.features.filter((f) => f.id !== id),
    }));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    try {
      const suggestion: Suggestion = JSON.parse(e.dataTransfer.getData('application/json'));
      handleAddSuggestion(suggestion);
    } catch (err) {
      console.error('Failed to add dragged suggestion:', err);
    }
  };

  const handleSavePRD = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Convert structured data to markdown using serializer
      const markdown = serializePRD(prdData);

      const response = await axios.post(`${API_URL}/api/prd/save`, {
        project_path: projectPath,
        prd_data: prdData,
        prd_markdown: markdown, // Send markdown version too
      });

      if (response.data.success) {
        setLastSaved(new Date());
        setLastFileModified(Date.now()); // Update to prevent re-parsing own save
        setSuccessMessage(`PRD saved to ${response.data.file_path}`);
        if (onSave) onSave();
      } else {
        setError(response.data.error || 'Failed to save PRD');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save PRD');
    } finally {
      setSaving(false);
    }
  };

  const addUserStory = () => {
    setPrdData((prev) => ({
      ...prev,
      user_stories: [
        ...prev.user_stories,
        'As a [user type], I want to [action], so that [benefit].',
      ],
    }));
  };

  const updateUserStory = (index: number, value: string) => {
    setPrdData((prev) => ({
      ...prev,
      user_stories: prev.user_stories.map((story, i) => (i === index ? value : story)),
    }));
  };

  const deleteUserStory = (index: number) => {
    setPrdData((prev) => ({
      ...prev,
      user_stories: prev.user_stories.filter((_, i) => i !== index),
    }));
  };

  const addSuccessCriterion = () => {
    setPrdData((prev) => ({
      ...prev,
      success_criteria: [...prev.success_criteria, 'New success criterion'],
    }));
  };

  const updateSuccessCriterion = (index: number, value: string) => {
    setPrdData((prev) => ({
      ...prev,
      success_criteria: prev.success_criteria.map((c, i) => (i === index ? value : c)),
    }));
  };

  const deleteSuccessCriterion = (index: number) => {
    setPrdData((prev) => ({
      ...prev,
      success_criteria: prev.success_criteria.filter((_, i) => i !== index),
    }));
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };

  const handleSuggestionsResizeStart = (e: React.MouseEvent) => {
    setIsResizingSuggestions(true);
    e.preventDefault();
  };

  return (
    <div className="interactive-prd-builder">
      <div className="prd-header">
        <div className="header-left">
          <h2>📝 {projectName} - PRD Builder</h2>
          <div className="section-tabs">
            <button
              className={`section-tab ${activeSection === 'features' ? 'active' : ''}`}
              onClick={() => setActiveSection('features')}
            >
              Features
            </button>
            <button
              className={`section-tab ${activeSection === 'stories' ? 'active' : ''}`}
              onClick={() => setActiveSection('stories')}
            >
              User Stories
            </button>
            <button
              className={`section-tab ${activeSection === 'technical' ? 'active' : ''}`}
              onClick={() => setActiveSection('technical')}
            >
              Technical
            </button>
            <button
              className={`section-tab ${activeSection === 'success' ? 'active' : ''}`}
              onClick={() => setActiveSection('success')}
            >
              Success
            </button>
          </div>
        </div>
        <div className="header-actions">
          {!projectPath && prdData.project_name && onCreateProject && (
            <button
              className="save-prd-btn"
              onClick={() => onCreateProject(prdData)}
              style={{ background: 'linear-gradient(135deg, #0e639c, #1177bb)' }}
            >
              📁 Create Project
            </button>
          )}
          <button
            className="save-prd-btn"
            onClick={handleSavePRD}
            disabled={saving || !projectPath}
          >
            {saving ? '💾 Saving...' : lastSaved ? '✅ Saved' : '💾 Save PRD'}
          </button>
        </div>
      </div>

      {(error || successMessage) && (
        <div className="message-bar">
          {error && <div className="error-message">❌ {error}</div>}
          {successMessage && <div className="success-message">✅ {successMessage}</div>}
        </div>
      )}

      <div className="prd-body">
        {/* Sidebar Navigation */}
        <div className="prd-sidebar" style={{ width: `${sidebarWidth}px` }}>
          <div className="prd-sidebar-header">PRD Sections</div>
          <div
            className={`prd-sidebar-section ${activeSection === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveSection('overview')}
          >
            📋 Overview
          </div>
          <div
            className={`prd-sidebar-section ${activeSection === 'features' ? 'active' : ''}`}
            onClick={() => setActiveSection('features')}
          >
            🎯 Features
          </div>
          <div
            className={`prd-sidebar-section ${activeSection === 'stories' ? 'active' : ''}`}
            onClick={() => setActiveSection('stories')}
          >
            👥 User Stories
          </div>
          <div
            className={`prd-sidebar-section ${activeSection === 'technical' ? 'active' : ''}`}
            onClick={() => setActiveSection('technical')}
          >
            ⚙️ Technical
          </div>
          <div
            className={`prd-sidebar-section ${activeSection === 'success' ? 'active' : ''}`}
            onClick={() => setActiveSection('success')}
          >
            ✅ Success Criteria
          </div>
        </div>

        {/* Resize Handle */}
        <div className="resize-handle" onMouseDown={handleResizeStart}></div>

        {/* Main Content Area */}
        <div className="prd-content" onDragOver={handleDragOver} onDrop={handleDrop}>
          {/* Overview Section */}
          {activeSection === 'overview' && (
            <div className="section-block overview-section">
              <div className="section-header">
                <h3>📋 Project Overview</h3>
              </div>

              <div className="overview-fields">
                <div className="field-group">
                  <label className="subsection-label subsection-name">Project Name</label>
                  <input
                    type="text"
                    className="name-input"
                    value={prdData.project_name}
                    onChange={(e) => setPrdData({ ...prdData, project_name: e.target.value })}
                    placeholder="Enter your project name..."
                  />
                </div>

                <div className="field-group">
                  <label className="subsection-label subsection-summary">Executive Summary</label>
                  <textarea
                    className="overview-input"
                    value={prdData.overview.executive_summary}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        overview: { ...prdData.overview, executive_summary: e.target.value },
                      })
                    }
                    placeholder="A concise summary of what the project does and why it matters..."
                    rows={6}
                  />
                </div>

                <div className="field-group">
                  <label className="subsection-label subsection-goals">Goals & Objectives</label>
                  <textarea
                    className="overview-input"
                    value={prdData.overview.goals}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        overview: { ...prdData.overview, goals: e.target.value },
                      })
                    }
                    placeholder="What are the main goals and objectives of this project?"
                    rows={6}
                  />
                </div>

                <div className="field-group">
                  <label className="subsection-label subsection-users">Target Users</label>
                  <textarea
                    className="overview-input"
                    value={prdData.overview.target_users}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        overview: { ...prdData.overview, target_users: e.target.value },
                      })
                    }
                    placeholder="Who are the target users? What are their needs and pain points?"
                    rows={6}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Features Section */}
          {activeSection === 'features' && (
            <div className="section-block features-section">
              <div className="section-header">
                <h3>🎯 Features</h3>
                <div className="header-controls">
                  <select
                    className="status-filter-select"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="all">All Status</option>
                    <option value="implemented">✅ Implemented</option>
                    <option value="partial">🟡 In Progress</option>
                    <option value="planned">📋 Planned</option>
                  </select>
                  <select
                    className="version-filter-select"
                    value={versionFilter}
                    onChange={(e) => setVersionFilter(e.target.value)}
                  >
                    <option value="all">All Versions</option>
                    <option value="current">Current (No Version)</option>
                    <option value="1.1.0">v1.1.0 (Patch)</option>
                    <option value="1.2.0">v1.2.0 (Minor)</option>
                    <option value="2.0.0">v2.0.0 (Major)</option>
                  </select>
                  <button
                    className="add-btn"
                    onClick={() =>
                      handleAddSuggestion({
                        title: 'New Feature',
                        description: 'Describe this feature...',
                        priority: 'medium',
                        rationale: '',
                      })
                    }
                  >
                    ➕ Add Feature
                  </button>
                </div>
              </div>
              <div className="features-list">
                {(() => {
                  // Filter features
                  const filteredFeatures = (prdData.features || []).filter((feature) => {
                    const matchesVersion =
                      versionFilter === 'all' ||
                      (versionFilter === 'current' && !feature.version) ||
                      feature.version === versionFilter;
                    const matchesStatus =
                      statusFilter === 'all' ||
                      (feature.status || 'planned') === statusFilter;
                    return matchesVersion && matchesStatus;
                  });

                  // Group features by group field
                  const groupedFeatures: { [key: string]: Feature[] } = {};
                  filteredFeatures.forEach((feature) => {
                    const groupName = feature.group || 'Other';
                    if (!groupedFeatures[groupName]) {
                      groupedFeatures[groupName] = [];
                    }
                    groupedFeatures[groupName].push(feature);
                  });

                  // Get sorted group names
                  const groupNames = Object.keys(groupedFeatures).sort();

                  // Toggle group collapse
                  const toggleGroup = (groupName: string) => {
                    setCollapsedGroups((prev) => {
                      const next = new Set(prev);
                      if (next.has(groupName)) {
                        next.delete(groupName);
                      } else {
                        next.add(groupName);
                      }
                      return next;
                    });
                  };

                  if (filteredFeatures.length === 0) {
                    return (
                      <div className="empty-hint">
                        {versionFilter === 'all' && statusFilter === 'all'
                          ? 'No features yet. Add one manually or drag from AI suggestions. →'
                          : `No features matching selected filters.`}
                      </div>
                    );
                  }

                  return groupNames.map((groupName) => {
                    const features = groupedFeatures[groupName];
                    const isCollapsed = collapsedGroups.has(groupName);

                    return (
                      <div key={groupName} className="feature-group">
                        <div
                          className="feature-group-header"
                          onClick={() => toggleGroup(groupName)}
                          style={{
                            cursor: 'pointer',
                            padding: '12px 16px',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            borderRadius: '8px',
                            marginBottom: isCollapsed ? '12px' : '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            color: 'white',
                            fontWeight: 600,
                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                          }}
                        >
                          <span>
                            {isCollapsed ? '▶' : '▼'} {groupName} ({features.length})
                          </span>
                        </div>
                        {!isCollapsed && (
                          <div className="feature-group-content" style={{ marginBottom: '16px' }}>
                            {features.map((feature) => (
                              <FeatureCard
                                key={feature.id}
                                feature={feature}
                                onUpdate={handleUpdateFeature}
                                onDelete={handleDeleteFeature}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}

          {/* User Stories Section */}
          {activeSection === 'stories' && (
            <div className="section-block stories-section">
              <div className="section-header">
                <h3>👥 User Stories</h3>
                <button className="add-btn" onClick={addUserStory}>
                  ➕ Add Story
                </button>
              </div>
              <div className="stories-list">
                {prdData.user_stories.map((story, index) => (
                  <div key={index} className="story-item">
                    <textarea
                      className="story-input"
                      value={story}
                      onChange={(e) => updateUserStory(index, e.target.value)}
                      rows={2}
                    />
                    <button className="delete-btn" onClick={() => deleteUserStory(index)}>
                      🗑️
                    </button>
                  </div>
                ))}
                {(prdData.user_stories || []).length === 0 && (
                  <div className="empty-hint">
                    No user stories yet. Click "Add Story" to create one.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Technical Requirements Section */}
          {activeSection === 'technical' && (
            <div className="section-block technical-section">
              <h3>⚙️ Technical Requirements</h3>
              <div className="tech-fields">
                <div className="tech-field">
                  <label>Frontend</label>
                  <input
                    type="text"
                    value={prdData.technical_requirements.frontend}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        technical_requirements: {
                          ...prdData.technical_requirements,
                          frontend: e.target.value,
                        },
                      })
                    }
                    placeholder="e.g., React, TypeScript, Tailwind CSS"
                  />
                </div>
                <div className="tech-field">
                  <label>Backend</label>
                  <input
                    type="text"
                    value={prdData.technical_requirements.backend}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        technical_requirements: {
                          ...prdData.technical_requirements,
                          backend: e.target.value,
                        },
                      })
                    }
                    placeholder="e.g., Python FastAPI, PostgreSQL"
                  />
                </div>
                <div className="tech-field">
                  <label>Database</label>
                  <input
                    type="text"
                    value={prdData.technical_requirements.database}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        technical_requirements: {
                          ...prdData.technical_requirements,
                          database: e.target.value,
                        },
                      })
                    }
                    placeholder="e.g., PostgreSQL, Redis"
                  />
                </div>
                <div className="tech-field">
                  <label>Infrastructure</label>
                  <input
                    type="text"
                    value={prdData.technical_requirements.infrastructure}
                    onChange={(e) =>
                      setPrdData({
                        ...prdData,
                        technical_requirements: {
                          ...prdData.technical_requirements,
                          infrastructure: e.target.value,
                        },
                      })
                    }
                    placeholder="e.g., Docker, AWS, GitHub Actions"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Success Criteria Section */}
          {activeSection === 'success' && (
            <div className="section-block success-section">
              <div className="section-header">
                <h3>✅ Success Criteria</h3>
                <button className="add-btn" onClick={addSuccessCriterion}>
                  ➕ Add Criterion
                </button>
              </div>
              <div className="criteria-list">
                {prdData.success_criteria.map((criterion, index) => (
                  <div key={index} className="criterion-item">
                    <input
                      type="text"
                      className="criterion-input"
                      value={criterion}
                      onChange={(e) => updateSuccessCriterion(index, e.target.value)}
                    />
                    <button className="delete-btn" onClick={() => deleteSuccessCriterion(index)}>
                      🗑️
                    </button>
                  </div>
                ))}
                {(prdData.success_criteria || []).length === 0 && (
                  <div className="empty-hint">
                    No success criteria yet. Click "Add Criterion" to create one.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Resize Handle for Suggestions Panel */}
        <div className="resize-handle resize-handle-suggestions" onMouseDown={handleSuggestionsResizeStart}></div>

        <div style={{ width: `${suggestionsWidth}px`, flexShrink: 0 }}>
          <SuggestionsPanel
            projectContext={{
              overview: prdData.overview,
              features: prdData.features,
            }}
            section={activeSection}
            subsection={undefined}
            onAddSuggestion={handleAddSuggestion}
            usedSuggestions={usedSuggestions}
            onRestoreSuggestions={() => setUsedSuggestions(new Set())}
            getSuggestionKey={getSuggestionKey}
          />
        </div>
      </div>
    </div>
  );
}
