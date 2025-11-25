/**
 * ProjectView - Split screen view for project planning
 * Left: PRD Editor with features and requirements
 * Right: Live Mermaid diagrams and AI suggestions
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { InteractivePRDBuilder } from '../components/InteractivePRDBuilder';
import { ArchitectureSection } from '../components/MermaidDiagram';
import { parsePRD } from '../utils/prdParser';
import axios from 'axios';
import './ProjectView.css';

const API_URL = 'http://localhost:8080';

export function ProjectView() {
  const { projectName } = useParams<{ projectName: string }>();
  const navigate = useNavigate();
  const [projectPath, setProjectPath] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDiagram, setShowDiagram] = useState(true);
  const [prdData, setPrdData] = useState<any>(null);

  useEffect(() => {
    if (!projectName) return;

    const loadProject = async () => {
      try {
        setLoading(true);
        setError(null);

        // Construct project path (process.env doesn't exist in browser)
        const path = `/Users/byronhudson/Projects/${projectName}`;
        setProjectPath(path);

        // Try to load PROJECT_SPEC.md
        try {
          const response = await axios.post(`${API_URL}/api/prd/read`, {
            project_path: path,
          });

          if (response.data.success && response.data.prd_markdown) {
            const parsed = parsePRD(response.data.prd_markdown);
            setPrdData(parsed);
          }
        } catch (err) {
          console.log('No PROJECT_SPEC.md yet - will be created during planning');
        }

        setLoading(false);
      } catch (err: any) {
        setError(err.message || 'Failed to load project');
        setLoading(false);
      }
    };

    loadProject();
  }, [projectName]);

  if (loading) {
    return (
      <div className="project-view-loading">
        <div className="spinner">🔄</div>
        <div>Loading {projectName}...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="project-view-error">
        <div className="error-icon">❌</div>
        <div className="error-message">{error}</div>
        <button onClick={() => navigate('/')}>← Back to Projects</button>
      </div>
    );
  }

  return (
    <div className="project-view">
      <div className="project-header">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← Projects
        </button>
        <h1>📋 {projectName}</h1>
        <div className="header-actions">
          <button
            className={`toggle-btn ${showDiagram ? 'active' : ''}`}
            onClick={() => setShowDiagram(!showDiagram)}
          >
            {showDiagram ? '📊 Hide Diagram' : '📊 Show Diagram'}
          </button>
        </div>
      </div>

      <div className={`project-content ${showDiagram ? 'split-view' : 'full-width'}`}>
        <div className="prd-panel">
          <InteractivePRDBuilder
            projectName={projectName || 'Project'}
            projectPath={projectPath}
            initialPRD={prdData}
          />
        </div>

        {showDiagram && (
          <div className="diagram-panel">
            <div className="panel-header">
              <h2>🏗️ Architecture</h2>
            </div>
            <div className="panel-content">
              {prdData?.architecture_diagram ? (
                <ArchitectureSection diagram={prdData.architecture_diagram} />
              ) : (
                <div className="diagram-placeholder">
                  <div className="placeholder-icon">🏗️</div>
                  <h3>Architecture Diagram</h3>
                  <p>Diagram will appear here as you plan</p>
                  <div className="placeholder-hint">
                    In planning mode, ask Claude to:
                    <ul>
                      <li>"Show me the system architecture"</li>
                      <li>"Create a diagram of the components"</li>
                    </ul>
                  </div>
                </div>
              )}

              {prdData?.external_services && prdData.external_services.length > 0 && (
                <div className="services-section">
                  <h3>🔌 External Services</h3>
                  {prdData.external_services.map((service: any, idx: number) => (
                    <div key={idx} className="service-card">
                      <div className="service-name">{service.name}</div>
                      <div className="service-provider">{service.provider}</div>
                      <div className="service-auth">{service.authentication}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
