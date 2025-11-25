/**
 * Attach Project Modal - Shows attach progress and results
 * Prompts user to attach BR when opening a project without it
 */

import { useState } from 'react';
import { projectAPI } from '../services/api';
import './AttachProjectModal.css';

interface AttachProjectModalProps {
  projectName: string;
  projectPath: string;
  onAttachComplete: (prdPath: string) => void;
  onCancel: () => void;
}

type AttachState = 'prompt' | 'attaching' | 'success' | 'error';

export function AttachProjectModal({
  projectName,
  projectPath,
  onAttachComplete,
  onCancel,
}: AttachProjectModalProps) {
  const [state, setState] = useState<AttachState>('prompt');
  const [error, setError] = useState<string | null>(null);
  const [output, setOutput] = useState<string>('');
  const [prdPath, setPrdPath] = useState<string | null>(null);
  const [alias, setAlias] = useState<string>('');

  const handleAttach = async () => {
    try {
      setState('attaching');
      setError(null);
      setOutput('');

      const result = await projectAPI.attachProject(projectPath, false);

      if (result.success) {
        // If alias was provided, set it
        if (alias && alias.trim()) {
          try {
            await projectAPI.setAlias(projectPath, alias.trim());
          } catch (aliasErr: any) {
            console.warn('Failed to set alias:', aliasErr);
            // Don't fail the whole attach process if alias fails
          }
        }

        setState('success');
        setOutput(result.output || '');
        setPrdPath(result.prd_path);
      } else {
        setState('error');
        setError(result.error || 'Failed to attach BuildRunner');
      }
    } catch (err: any) {
      setState('error');
      setError(err.message || 'Failed to attach BuildRunner');
    }
  };

  const handleComplete = () => {
    if (prdPath) {
      onAttachComplete(prdPath);
    }
  };

  return (
    <div className="attach-modal-overlay" onClick={state === 'attaching' ? undefined : onCancel}>
      <div className="attach-modal" onClick={(e) => e.stopPropagation()}>
        {state === 'prompt' && (
          <>
            <div className="attach-modal-header">
              <h2>🔗 Attach BuildRunner</h2>
            </div>
            <div className="attach-modal-body">
              <div className="attach-prompt">
                <div className="project-icon-large">📁</div>
                <h3>{projectName}</h3>
                <p className="attach-description">
                  BuildRunner is not attached to this project. Would you like to:
                </p>
                <ul className="attach-benefits">
                  <li>✨ Scan the codebase for existing features</li>
                  <li>📝 Generate a complete PROJECT_SPEC.md</li>
                  <li>🚀 Start managing the project with BuildRunner</li>
                </ul>
                <p className="attach-note">
                  This process will analyze your code and create a PRD that you can review and edit.
                </p>
                <div className="alias-input-container">
                  <input
                    type="text"
                    placeholder="Optional: Set alias (e.g., 'myapp')"
                    value={alias}
                    onChange={(e) => setAlias(e.target.value)}
                    className="alias-input"
                  />
                  <p className="alias-hint">
                    Use aliases to quickly jump to projects: <code>br alias jump myapp</code>
                  </p>
                </div>
              </div>
            </div>
            <div className="attach-modal-footer">
              <button className="cancel-btn" onClick={onCancel}>
                Cancel
              </button>
              <button className="attach-btn" onClick={handleAttach}>
                🔗 Attach BuildRunner
              </button>
            </div>
          </>
        )}

        {state === 'attaching' && (
          <>
            <div className="attach-modal-header">
              <h2>🔍 Scanning Project...</h2>
            </div>
            <div className="attach-modal-body">
              <div className="attaching-state">
                <div className="spinner-large"></div>
                <h3>Analyzing {projectName}</h3>
                <div className="attach-steps">
                  <div className="attach-step active">
                    <span className="step-icon">📂</span>
                    <span>Scanning codebase...</span>
                  </div>
                  <div className="attach-step active">
                    <span className="step-icon">🧩</span>
                    <span>Extracting features...</span>
                  </div>
                  <div className="attach-step active">
                    <span className="step-icon">📝</span>
                    <span>Generating PRD...</span>
                  </div>
                </div>
                <p className="attach-wait">This may take a moment...</p>
              </div>
            </div>
          </>
        )}

        {state === 'success' && (
          <>
            <div className="attach-modal-header success">
              <h2>✅ Attach Complete!</h2>
            </div>
            <div className="attach-modal-body">
              <div className="success-state">
                <div className="success-icon">🎉</div>
                <h3>BuildRunner Successfully Attached</h3>
                <p className="success-message">
                  Your project has been scanned and a PROJECT_SPEC.md has been generated.
                </p>
                <div className="success-details">
                  <div className="detail-item">
                    <span className="detail-label">Project:</span>
                    <span className="detail-value">{projectName}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">PRD Location:</span>
                    <span className="detail-value">{prdPath}</span>
                  </div>
                  {alias && alias.trim() && (
                    <div className="detail-item">
                      <span className="detail-label">Alias:</span>
                      <span className="detail-value">
                        {alias.trim()} (use <code>br alias jump {alias.trim()}</code>)
                      </span>
                    </div>
                  )}
                </div>
                {output && (
                  <details className="output-details">
                    <summary>View Scan Output</summary>
                    <pre className="output-text">{output}</pre>
                  </details>
                )}
              </div>
            </div>
            <div className="attach-modal-footer">
              <button className="complete-btn" onClick={handleComplete}>
                Open Project →
              </button>
            </div>
          </>
        )}

        {state === 'error' && (
          <>
            <div className="attach-modal-header error">
              <h2>❌ Attach Failed</h2>
            </div>
            <div className="attach-modal-body">
              <div className="error-state-modal">
                <div className="error-icon">⚠️</div>
                <h3>Failed to Attach BuildRunner</h3>
                <p className="error-message-modal">{error}</p>
                <p className="error-suggestion">
                  You can try attaching manually using the CLI:
                </p>
                <code className="cli-command">
                  cd {projectPath}
                  <br />
                  br attach attach
                </code>
              </div>
            </div>
            <div className="attach-modal-footer">
              <button className="cancel-btn" onClick={onCancel}>
                Close
              </button>
              <button className="retry-btn-modal" onClick={handleAttach}>
                🔄 Try Again
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
