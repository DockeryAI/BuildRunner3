/**
 * Project Picker - Select existing projects from ~/Projects
 * Supports attaching BR to projects without BuildRunner
 */

import { useState, useEffect } from 'react';
import { projectAPI } from '../services/api';
import './ProjectPicker.css';

interface Project {
  name: string;
  path: string;
  has_venv: boolean;
  has_buildrunner: boolean;
  created: number;
}

interface ProjectPickerProps {
  onProjectSelect: (project: Project) => void;
  onClose: () => void;
}

export function ProjectPicker({ onProjectSelect, onClose }: ProjectPickerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await projectAPI.listProjects();

      if (result.success) {
        setProjects(result.projects);
      } else {
        setError(result.error || 'Failed to load projects');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="project-picker-overlay" onClick={onClose}>
      <div className="project-picker-modal" onClick={(e) => e.stopPropagation()}>
        <div className="project-picker-header">
          <h2>📁 Select Project</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="project-picker-search">
          <input
            type="text"
            placeholder="🔍 Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="project-picker-body">
          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Loading projects...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p className="error-message">❌ {error}</p>
              <button onClick={loadProjects} className="retry-btn">
                🔄 Retry
              </button>
            </div>
          )}

          {!loading && !error && filteredProjects.length === 0 && (
            <div className="empty-state">
              {searchQuery ? (
                <>
                  <p>No projects match "{searchQuery}"</p>
                  <button onClick={() => setSearchQuery('')} className="clear-search-btn">
                    Clear Search
                  </button>
                </>
              ) : (
                <>
                  <p>No projects found in ~/Projects</p>
                  <p className="hint">Create a new project to get started</p>
                </>
              )}
            </div>
          )}

          {!loading && !error && filteredProjects.length > 0 && (
            <div className="projects-list">
              {filteredProjects.map((project) => (
                <div
                  key={project.path}
                  className="project-item"
                  onClick={() => onProjectSelect(project)}
                >
                  <div className="project-icon">
                    {project.has_buildrunner ? '🚀' : '📁'}
                  </div>
                  <div className="project-info">
                    <div className="project-name">{project.name}</div>
                    <div className="project-meta">
                      <span className="project-date">
                        {formatDate(project.created)}
                      </span>
                      {project.has_venv && (
                        <span className="project-badge">🐍 venv</span>
                      )}
                      {project.has_buildrunner ? (
                        <span className="project-badge br-attached">✅ BR Attached</span>
                      ) : (
                        <span className="project-badge br-not-attached">❌ Not Attached</span>
                      )}
                    </div>
                  </div>
                  <div className="project-arrow">→</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="project-picker-footer">
          <p className="project-count">
            {filteredProjects.length} {filteredProjects.length === 1 ? 'project' : 'projects'} found
          </p>
        </div>
      </div>
    </div>
  );
}
