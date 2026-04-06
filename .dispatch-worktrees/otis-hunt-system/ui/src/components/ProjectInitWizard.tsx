/**
 * ProjectInitWizard Component
 * Simplified wizard for creating new projects with PRD
 * New Flow: Description → PRD Builder → Create Project
 */

import React, { useState } from 'react';
import axios from 'axios';
import './ProjectInitWizard.css';

const API_URL = 'http://localhost:8080';

type WizardStep = 'description' | 'parsing';

interface ProjectInitWizardProps {
  onComplete: (projectData: {
    description: string;
    parsedPRD: any;
  }) => void;
  onCancel: () => void;
}

export function ProjectInitWizard({ onComplete, onCancel }: ProjectInitWizardProps) {
  const [step, setStep] = useState<WizardStep>('description');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState('');

  const handleParseDescription = async () => {
    if (!description.trim()) {
      setError('Please enter a project description');
      return;
    }

    setStep('parsing');
    setError(null);
    setProgress('AI is analyzing your description...');

    try {
      const response = await axios.post(`${API_URL}/api/prd/parse`, {
        description: description.trim(),
      });

      if (response.data.success) {
        setProgress('PRD generated successfully!');
        setTimeout(() => {
          onComplete({
            description: description.trim(),
            parsedPRD: response.data.prd,
          });
        }, 500);
      } else {
        setError(response.data.error || 'Failed to parse description');
        setStep('description');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to parse description');
      setStep('description');
    }
  };

  return (
    <div className="project-init-wizard">
      <div className="wizard-modal">
        <div className="wizard-header">
          <h2>🚀 Describe Your Project</h2>
          <button className="close-btn" onClick={onCancel}>
            ✕
          </button>
        </div>

        <div className="wizard-body">
          {/* Step 1: Project Description */}
          {step === 'description' && (
            <div className="wizard-step">
              <div className="step-icon">💡</div>
              <h3>What do you want to build?</h3>
              <p className="step-description">
                Describe your project idea. AI will generate a structured PRD that you can refine before creating the project.
              </p>
              <textarea
                className="description-textarea"
                placeholder="Example: Build a task management app with real-time collaboration. Users can create projects, assign tasks, set deadlines, and track progress. Include notifications, file attachments, and team chat."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={12}
                autoFocus
              />
              {error && <div className="error-box">{error}</div>}
              <div className="step-actions">
                <button className="cancel-btn" onClick={onCancel}>
                  Cancel
                </button>
                <button
                  className="next-btn"
                  onClick={handleParseDescription}
                  disabled={!description.trim()}
                >
                  Generate PRD with AI →
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Parsing Description */}
          {step === 'parsing' && (
            <div className="wizard-step">
              <div className="step-icon loading">🤖</div>
              <h3>AI is creating your PRD...</h3>
              <p className="progress-text">{progress}</p>
              <div className="progress-bar">
                <div className="progress-fill"></div>
              </div>
              <p className="hint">This usually takes 5-10 seconds</p>
            </div>
          )}
        </div>
      </div>

      <div className="wizard-overlay" onClick={onCancel}></div>
    </div>
  );
}
