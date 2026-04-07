import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import './ProjectInitModal.css';

interface ProjectInitModalProps {
  isOpen: boolean;
  onClose: () => void;
  prdData: any;
}

interface ValidationState {
  isValid: boolean;
  isChecking: boolean;
  message?: string;
}

interface ChecklistItem {
  id: string;
  label: string;
  checked: boolean;
  isAutoChecked: boolean;
}

const ALIAS_REGEX = /^[a-zA-Z0-9_-]+$/;
const DEBOUNCE_DELAY = 300;

const ProjectInitModal: React.FC<ProjectInitModalProps> = ({
  isOpen,
  onClose,
  prdData,
}) => {
  const navigate = useNavigate();
  const [alias, setAlias] = useState('');
  const [projectPath, setProjectPath] = useState('');
  const [aliasValidation, setAliasValidation] = useState<ValidationState>({
    isValid: false,
    isChecking: false,
  });
  const [pathValidation, setPathValidation] = useState<ValidationState>({
    isValid: false,
    isChecking: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([
    {
      id: 'prd-complete',
      label: 'PRD complete',
      checked: true,
      isAutoChecked: true,
    },
    {
      id: 'architecture-defined',
      label: 'Architecture defined',
      checked: true,
      isAutoChecked: true,
    },
    {
      id: 'alias-available',
      label: 'Alias available',
      checked: false,
      isAutoChecked: false,
    },
    {
      id: 'path-valid',
      label: 'Path valid',
      checked: false,
      isAutoChecked: false,
    },
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, isSubmitting, onClose]);

  // Validate alias format
  const validateAliasFormat = (value: string): boolean => {
    if (!value) return false;
    return ALIAS_REGEX.test(value);
  };

  // Check alias availability via API
  const checkAliasAvailability = useCallback(async (aliasValue: string) => {
    if (!validateAliasFormat(aliasValue)) {
      setAliasValidation({
        isValid: false,
        isChecking: false,
        message: 'Alias must contain only letters, numbers, hyphens, and underscores',
      });
      updateChecklistItem('alias-available', false);
      return;
    }

    setAliasValidation({
      isValid: false,
      isChecking: true,
    });

    try {
      const response = await axios.get(`/api/build/aliases/${aliasValue}`);

      // If alias exists, it's not available
      if (response.data && response.data.exists) {
        setAliasValidation({
          isValid: false,
          isChecking: false,
          message: 'This alias is already in use',
        });
        updateChecklistItem('alias-available', false);
      } else {
        setAliasValidation({
          isValid: true,
          isChecking: false,
          message: 'Alias is available',
        });
        updateChecklistItem('alias-available', true);
      }
    } catch (error) {
      // If 404, alias is available
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        setAliasValidation({
          isValid: true,
          isChecking: false,
          message: 'Alias is available',
        });
        updateChecklistItem('alias-available', true);
      } else {
        setAliasValidation({
          isValid: false,
          isChecking: false,
          message: 'Failed to check alias availability',
        });
        updateChecklistItem('alias-available', false);
      }
    }
  }, []);

  // Debounced alias validation
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (alias) {
      debounceTimerRef.current = setTimeout(() => {
        checkAliasAvailability(alias);
      }, DEBOUNCE_DELAY);
    } else {
      setAliasValidation({
        isValid: false,
        isChecking: false,
      });
      updateChecklistItem('alias-available', false);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [alias, checkAliasAvailability]);

  // Validate project path
  const validateProjectPath = useCallback(async (path: string) => {
    if (!path) {
      setPathValidation({
        isValid: false,
        isChecking: false,
      });
      updateChecklistItem('path-valid', false);
      return;
    }

    setPathValidation({
      isValid: false,
      isChecking: true,
    });

    try {
      // Simple validation: check if path is non-empty and looks like a valid path
      // In a real implementation, you might want to validate the path server-side
      const isValidPath = path.length > 0 && (
        path.startsWith('/') ||
        path.match(/^[a-zA-Z]:\\/) ||
        path.startsWith('~/')
      );

      if (isValidPath) {
        setPathValidation({
          isValid: true,
          isChecking: false,
          message: 'Path is valid',
        });
        updateChecklistItem('path-valid', true);
      } else {
        setPathValidation({
          isValid: false,
          isChecking: false,
          message: 'Please enter a valid absolute path',
        });
        updateChecklistItem('path-valid', false);
      }
    } catch (error) {
      setPathValidation({
        isValid: false,
        isChecking: false,
        message: 'Failed to validate path',
      });
      updateChecklistItem('path-valid', false);
    }
  }, []);

  // Update path validation when path changes
  useEffect(() => {
    validateProjectPath(projectPath);
  }, [projectPath, validateProjectPath]);

  // Update checklist item
  const updateChecklistItem = (id: string, checked: boolean) => {
    setChecklist((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, checked } : item
      )
    );
  };

  // Handle alias input change
  const handleAliasChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAlias(e.target.value);
  };

  // Handle project path input change
  const handleProjectPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProjectPath(e.target.value);
  };

  // Handle file picker button click
  const handleFilePickerClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Handle file selection
  const handleFileSelection = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Get the directory path from the first file
      const file = files[0];
      // In a real implementation, you'd use the webkitdirectory attribute
      // For now, we'll just use the file path as-is
      const path = (file as any).path || file.name;
      setProjectPath(path);
    }
  };

  // Check if all checklist items are checked
  const allChecksPassed = checklist.every((item) => item.checked);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!allChecksPassed || isSubmitting) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await axios.post('/api/build/init', {
        alias,
        project_path: projectPath,
        prd_data: prdData,
      });

      toast.success('Project initialized successfully!');

      // Redirect to build page
      navigate(`/build/${alias}`);
    } catch (error) {
      console.error('Failed to initialize project:', error);

      if (axios.isAxiosError(error)) {
        const message = error.response?.data?.error || 'Failed to initialize project';
        toast.error(message);
      } else {
        toast.error('An unexpected error occurred');
      }

      setIsSubmitting(false);
    }
  };

  // Handle modal close
  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  // Handle overlay click
  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="project-init-modal-overlay"
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="project-init-modal-card">
        <div className="project-init-modal-header">
          <h2 id="modal-title">Initialize Project</h2>
          <button
            className="project-init-modal-close"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close modal"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M18 6L6 18M6 6l12 12" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="project-init-modal-form">
          <div className="project-init-form-section">
            <label htmlFor="project-alias" className="project-init-label">
              Project Alias
              <span className="project-init-required">*</span>
            </label>
            <div className="project-init-input-wrapper">
              <input
                id="project-alias"
                type="text"
                className={`project-init-input ${
                  aliasValidation.isChecking
                    ? 'project-init-input-loading'
                    : aliasValidation.isValid
                    ? 'project-init-input-valid'
                    : alias
                    ? 'project-init-input-invalid'
                    : ''
                }`}
                value={alias}
                onChange={handleAliasChange}
                placeholder="my-awesome-project"
                disabled={isSubmitting}
                aria-describedby="alias-validation-message"
                aria-invalid={alias && !aliasValidation.isValid}
              />
              <div className="project-init-input-icon">
                {aliasValidation.isChecking && (
                  <div className="project-init-spinner" aria-label="Checking alias availability"></div>
                )}
                {!aliasValidation.isChecking && aliasValidation.isValid && (
                  <svg
                    className="project-init-checkmark"
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path d="M16 6L8 14L4 10" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
                {!aliasValidation.isChecking && alias && !aliasValidation.isValid && (
                  <svg
                    className="project-init-error-icon"
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                  >
                    <circle cx="10" cy="10" r="8" strokeWidth="2" />
                    <path d="M10 6v4M10 14h.01" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                )}
              </div>
            </div>
            {aliasValidation.message && (
              <p
                id="alias-validation-message"
                className={`project-init-validation-message ${
                  aliasValidation.isValid
                    ? 'project-init-validation-success'
                    : 'project-init-validation-error'
                }`}
              >
                {aliasValidation.message}
              </p>
            )}
          </div>

          <div className="project-init-form-section">
            <label htmlFor="project-path" className="project-init-label">
              Project Path
              <span className="project-init-required">*</span>
            </label>
            <div className="project-init-path-input-group">
              <div className="project-init-input-wrapper">
                <input
                  id="project-path"
                  type="text"
                  className={`project-init-input ${
                    pathValidation.isChecking
                      ? 'project-init-input-loading'
                      : pathValidation.isValid
                      ? 'project-init-input-valid'
                      : projectPath
                      ? 'project-init-input-invalid'
                      : ''
                  }`}
                  value={projectPath}
                  onChange={handleProjectPathChange}
                  placeholder="/path/to/project"
                  disabled={isSubmitting}
                  aria-describedby="path-validation-message"
                  aria-invalid={projectPath && !pathValidation.isValid}
                />
                <div className="project-init-input-icon">
                  {pathValidation.isChecking && (
                    <div className="project-init-spinner" aria-label="Validating path"></div>
                  )}
                  {!pathValidation.isChecking && pathValidation.isValid && (
                    <svg
                      className="project-init-checkmark"
                      width="20"
                      height="20"
                      viewBox="0 0 20 20"
                      fill="none"
                      stroke="currentColor"
                    >
                      <path d="M16 6L8 14L4 10" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              </div>
              <button
                type="button"
                className="project-init-file-picker-button"
                onClick={handleFilePickerClick}
                disabled={isSubmitting}
                aria-label="Browse for project directory"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor">
                  <path
                    d="M3 7V5a2 2 0 012-2h3.586a1 1 0 01.707.293l1.414 1.414a1 1 0 00.707.293H15a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Browse
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="project-init-file-input"
                onChange={handleFileSelection}
                aria-hidden="true"
                tabIndex={-1}
              />
            </div>
            {pathValidation.message && (
              <p
                id="path-validation-message"
                className={`project-init-validation-message ${
                  pathValidation.isValid
                    ? 'project-init-validation-success'
                    : 'project-init-validation-error'
                }`}
              >
                {pathValidation.message}
              </p>
            )}
          </div>

          <div className="project-init-form-section">
            <h3 className="project-init-checklist-title">Pre-flight Checklist</h3>
            <ul className="project-init-checklist" role="list">
              {checklist.map((item, index) => (
                <li
                  key={item.id}
                  className={`project-init-checklist-item ${
                    item.checked ? 'project-init-checklist-item-checked' : ''
                  }`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="project-init-checkbox">
                    {item.checked && (
                      <svg
                        className="project-init-checkbox-checkmark"
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                      >
                        <path
                          d="M13 4L6 11L3 8"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                  <span className="project-init-checklist-label">{item.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="project-init-modal-footer">
            <button
              type="button"
              className="project-init-button project-init-button-secondary"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="project-init-button project-init-button-primary"
              disabled={!allChecksPassed || isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="project-init-button-spinner"></div>
                  Initializing...
                </>
              ) : (
                'Initialize Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectInitModal;
