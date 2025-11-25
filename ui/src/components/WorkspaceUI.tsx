/**
 * Workspace UI - Integrated BuildRunner Interface
 * Combines Command Center, PRD Editor, and Log Viewer
 */

import { useState } from 'react';
import { CommandCenter } from './CommandCenter';
import { PRDEditor } from './PRDEditor';
import { LogViewer } from './LogViewer';
import { ProjectInitWizard } from './ProjectInitWizard';
import { InteractivePRDBuilder } from './InteractivePRDBuilder';
import { ProjectPicker } from './ProjectPicker';
import { AttachProjectModal } from './AttachProjectModal';
import './WorkspaceUI.css';

// Declare Electron API types
declare global {
  interface Window {
    electronAPI?: {
      executeCommand: (command: string, cwd?: string) => Promise<any>;
      launchClaude: (projectName: string, prompt: string) => Promise<any>;
      openProjectFolder: (path: string) => Promise<void>;
      readFile: (path: string) => Promise<any>;
      writeFile: (path: string, content: string) => Promise<any>;
    };
  }
}

type TabType = 'command' | 'prd' | 'interactive-prd' | 'logs';

export function WorkspaceUI() {
  const [activeTab, setActiveTab] = useState<TabType>('command');
  const [currentProject, setCurrentProject] = useState<string>('');
  const [currentProjectPath, setCurrentProjectPath] = useState<string>('');
  const [showWizard, setShowWizard] = useState(false);
  const [parsedPRD, setParsedPRD] = useState<any>(null);
  const [projectDescription, setProjectDescription] = useState<string>('');
  const [showProjectPicker, setShowProjectPicker] = useState(false);
  const [showAttachModal, setShowAttachModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<any>(null);

  const handleProjectChange = (projectName: string) => {
    setCurrentProject(projectName);
  };

  const handleWizardComplete = async (projectData: {
    description: string;
    parsedPRD: any;
  }) => {
    // Store the description and parsed PRD, but don't create project yet
    setProjectDescription(projectData.description);
    setParsedPRD(projectData.parsedPRD);
    setShowWizard(false);
    setActiveTab('interactive-prd');
    // Project will be created when user clicks "Create Project" in PRD Builder
  };

  const handleCreateProject = async (prdData: any) => {
    try {
      const response = await fetch(`http://localhost:8080/api/project/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: prdData.project_name,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setCurrentProject(prdData.project_name);
        setCurrentProjectPath(data.project_path);

        // Save the PRD
        await fetch(`http://localhost:8080/api/prd/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: data.project_path,
            prd_data: prdData,
          }),
        });

        // Auto-launch planning mode
        if (window.electronAPI) {
          await launchPlanningMode(prdData.project_name, data.project_path);
        }

        alert(`Project "${prdData.project_name}" created successfully!`);
      } else {
        alert(`Failed to create project: ${data.error}`);
      }
    } catch (error: any) {
      alert(`Error creating project: ${error.message}`);
    }
  };

  const handlePRDSave = () => {
    // PRD saved - could show a success message or navigate somewhere
    console.log('PRD saved successfully');
  };

  const handleProjectSelect = async (project: any) => {
    setSelectedProject(project);
    setShowProjectPicker(false);

    // Check if project has BuildRunner attached
    if (project.has_buildrunner) {
      // Project already has BR, load and parse the PRD
      setCurrentProject(project.name);
      setCurrentProjectPath(project.path);

      // Try to parse existing PROJECT_SPEC.md into interactive format
      try {
        const response = await fetch(`http://localhost:8080/api/prd/parse-markdown`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_path: project.path }),
        });

        const data = await response.json();

        if (data.success && data.prd_data && data.prd_data.features && data.prd_data.features.length > 0) {
          // PRD has features, load into Interactive PRD Builder
          setParsedPRD(data.prd_data);
          setActiveTab('interactive-prd');
        } else {
          // No features in PRD, try scanning codebase
          console.log('No features found in PRD, scanning codebase...');
          try {
            const discoveryResponse = await fetch(`http://localhost:8080/api/prd/discover-features`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                project_path: project.path
              }),
            });

            const discoveryData = await discoveryResponse.json();

            if (discoveryData.success && discoveryData.prd_data) {
              console.log(`✅ Discovered ${discoveryData.features_discovered} features from codebase`);
              setParsedPRD(discoveryData.prd_data);
              setActiveTab('interactive-prd');
            } else {
              console.log('❌ Feature discovery failed, showing empty PRD editor');
              setActiveTab('prd');
            }
          } catch (discoveryError) {
            console.error('Failed to discover features from codebase:', discoveryError);
            setActiveTab('prd');
          }
        }
      } catch (error) {
        console.error('Failed to parse PRD:', error);
        setActiveTab('prd');
      }
    } else {
      // Project doesn't have BR, show attach modal
      setShowAttachModal(true);
    }
  };

  const handleAttachComplete = async (prdPath: string) => {
    // After successful attach, parse and load the project
    if (selectedProject) {
      setCurrentProject(selectedProject.name);
      setCurrentProjectPath(selectedProject.path);
      setShowAttachModal(false);

      // Try to parse the newly created PROJECT_SPEC.md
      try {
        const response = await fetch(`http://localhost:8080/api/prd/parse-markdown`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_path: selectedProject.path }),
        });

        const data = await response.json();

        if (data.success && data.prd_data) {
          // Load into Interactive PRD Builder
          setParsedPRD(data.prd_data);
          setActiveTab('interactive-prd');
        } else {
          // Fallback to regular editor
          setActiveTab('prd');
        }
      } catch (error) {
        console.error('Failed to parse attached PRD:', error);
        setActiveTab('prd');
      }
    }
  };

  const launchPlanningMode = async (projectName: string, projectPath: string) => {
    try {
      if (!window.electronAPI) {
        alert('Planning mode requires Electron desktop app');
        return;
      }

      const planningPrompt = `Project: ${projectName}

I just created a new project at: ${projectPath}

The PROJECT_SPEC.md has been generated with the PRD.

Please help me plan the implementation by:
1. Reviewing the PROJECT_SPEC.md
2. Breaking down the features into tasks
3. Creating an implementation plan

Start by reading the PROJECT_SPEC.md file and let's begin planning!`;

      await window.electronAPI.launchClaude(projectName, planningPrompt);
      console.log('Planning mode launched for:', projectName);
    } catch (error) {
      console.error('Failed to launch planning mode:', error);
      alert('Failed to launch planning mode. Please run "br plan" manually in the terminal.');
    }
  };

  return (
    <div className="workspace-ui">
      <div className="workspace-header">
        <div className="header-content">
          <h1>🚀 BuildRunner Workspace</h1>
          {currentProject && (
            <div className="project-indicator">
              📁 Current Project: <strong>{currentProject}</strong>
            </div>
          )}
          <div style={{ display: 'flex', gap: '12px' }}>
            {currentProject && currentProjectPath && (
              <button
                className="new-project-btn"
                onClick={() => launchPlanningMode(currentProject, currentProjectPath)}
                style={{ background: 'linear-gradient(135deg, #7c3aed, #9333ea)' }}
              >
                🧠 Start Planning
              </button>
            )}
            <button className="new-project-btn" onClick={() => setShowProjectPicker(true)}>
              📁 Open Project
            </button>
            <button className="new-project-btn" onClick={() => setShowWizard(true)}>
              ✨ New Project
            </button>
          </div>
        </div>

        <div className="tab-navigation">
          <button
            className={`tab-btn ${activeTab === 'command' ? 'active' : ''}`}
            onClick={() => setActiveTab('command')}
          >
            ⚡ Command Center
          </button>
          {parsedPRD && (
            <button
              className={`tab-btn ${activeTab === 'interactive-prd' ? 'active' : ''}`}
              onClick={() => setActiveTab('interactive-prd')}
            >
              ✨ PRD Builder
            </button>
          )}
          <button
            className={`tab-btn ${activeTab === 'prd' ? 'active' : ''}`}
            onClick={() => setActiveTab('prd')}
          >
            📝 PRD Editor
          </button>
          <button
            className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
          >
            📊 Live Logs
          </button>
        </div>
      </div>

      <div className="workspace-body">
        {activeTab === 'command' && (
          <div className="tab-content">
            <CommandCenter />
          </div>
        )}

        {activeTab === 'interactive-prd' && parsedPRD && (
          <div className="tab-content">
            <InteractivePRDBuilder
              projectName={parsedPRD.project_name || currentProject || 'New Project'}
              projectPath={currentProjectPath}
              initialPRD={parsedPRD}
              onSave={handlePRDSave}
              onCreateProject={handleCreateProject}
            />
          </div>
        )}

        {activeTab === 'prd' && (
          <div className="tab-content">
            {currentProject ? (
              <PRDEditor
                projectName={currentProject}
                projectPath={currentProjectPath}
                onSave={(content) => {
                  console.log('PRD saved:', content.substring(0, 100) + '...');
                }}
              />
            ) : (
              <div className="no-project-message">
                <div className="empty-state">
                  <h2>📁 No Project Selected</h2>
                  <p>
                    Please initialize a project first using the Command Center.
                  </p>
                  <button
                    onClick={() => setActiveTab('command')}
                    className="go-to-command-btn"
                  >
                    Go to Command Center
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="tab-content">
            <LogViewer projectName={currentProject} autoScroll={true} />
          </div>
        )}
      </div>

      <div className="workspace-footer">
        <div className="footer-content">
          <span className="version">BuildRunner v3.2.0</span>
          <span className="separator">|</span>
          <span className="info">
            File-based workspace integration with Claude Code
          </span>
        </div>
      </div>

      {showWizard && (
        <ProjectInitWizard
          onComplete={handleWizardComplete}
          onCancel={() => setShowWizard(false)}
        />
      )}

      {showProjectPicker && (
        <ProjectPicker
          onProjectSelect={handleProjectSelect}
          onClose={() => setShowProjectPicker(false)}
        />
      )}

      {showAttachModal && selectedProject && (
        <AttachProjectModal
          projectName={selectedProject.name}
          projectPath={selectedProject.path}
          onAttachComplete={handleAttachComplete}
          onCancel={() => {
            setShowAttachModal(false);
            setSelectedProject(null);
          }}
        />
      )}
    </div>
  );
}
