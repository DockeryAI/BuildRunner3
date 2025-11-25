/**
 * CommandCenter - The REAL BuildRunner UI
 *
 * Execute any BuildRunner command from the web interface
 */

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './CommandCenter.css';

const API_URL = 'http://localhost:8080';

// Check if running in Electron
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

const isElectron = window.electronAPI !== undefined;

interface CommandResult {
  output: string;
  error?: string;
  timestamp: Date;
  command: string;
}

export function CommandCenter() {
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<CommandResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [projectPath, setProjectPath] = useState('/Users/byronhudson/Projects/BuildRunner3');
  const [lastInitProject, setLastInitProject] = useState<string | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  // Common commands
  const commands = {
    init: async (name: string) => {
      const result = await executeCommand(`br init ${name}`);
      if (result && !result.error) {
        setLastInitProject(name);
        // Add helpful next steps message
        const helpMessage: CommandResult = {
          command: '# Next Steps',
          output: `✅ Project "${name}" initialized successfully!\n\n` +
                  `📁 Location: ${projectPath}/${name}\n\n` +
                  `Next steps:\n` +
                  `1. Run "br plan" in the terminal below to start planning mode\n` +
                  `2. Or run "br prd" to create a Product Requirements Document\n` +
                  `3. Then run "br run" to start the AI-powered build process\n\n` +
                  `Note: Claude integration works through the CLI. The UI cannot automatically open desktop apps.`,
          timestamp: new Date()
        };
        setHistory(prev => [...prev, helpMessage]);
      }
      return result;
    },
    run: async () => {
      return await executeCommand('br run');
    },
    status: async () => {
      return await executeCommand('br status');
    },
    taskList: async () => {
      return await executeCommand('br task list');
    },
    qualityCheck: async () => {
      return await executeCommand('br quality check');
    },
    agentList: async () => {
      return await executeCommand('br agent list');
    },
  };

  const executeCommand = async (cmd: string) => {
    setLoading(true);
    try {
      let result: CommandResult;

      // Use Electron API if available (native execution)
      if (isElectron && window.electronAPI) {
        const electronResult = await window.electronAPI.executeCommand(cmd, projectPath);
        result = {
          command: cmd,
          output: electronResult.output || '',
          error: electronResult.error,
          timestamp: new Date()
        };
      } else {
        // Fall back to web API
        const response = await axios.post(`${API_URL}/api/execute`, {
          command: cmd,
          cwd: projectPath
        });

        result = {
          command: cmd,
          output: response.data.output || response.data,
          error: response.data.error,
          timestamp: new Date()
        };
      }

      setHistory(prev => [...prev, result]);
      return result;
    } catch (error: any) {
      const result: CommandResult = {
        command: cmd,
        output: '',
        error: error.response?.data?.detail || error.message,
        timestamp: new Date()
      };
      setHistory(prev => [...prev, result]);
      return result;
    } finally {
      setLoading(false);
      setCommand('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      await executeCommand(command);
    }
  };

  useEffect(() => {
    // Auto-scroll to bottom when new output
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  return (
    <div className="command-center">
      <div className="header">
        <h1>🚀 BuildRunner Command Center</h1>
        <div className="subtitle">
          {isElectron ? (
            <span style={{ color: '#00ff00' }}>
              ⚡ Electron Mode - Full Native Control (Claude launching enabled!)
            </span>
          ) : (
            'Execute any BR command from the web'
          )}
        </div>
      </div>

      <div className="quick-actions">
        <h3>Quick Actions</h3>
        <div className="action-buttons">
          <div className="action-group">
            <input
              type="text"
              placeholder="Project name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="project-input"
            />
            <button
              onClick={() => commands.init(projectName)}
              disabled={!projectName || loading}
              className="action-btn init"
            >
              📁 Init Project
            </button>
          </div>

          <button
            onClick={commands.run}
            disabled={loading}
            className="action-btn run"
          >
            ▶️ Run Build
          </button>

          <button
            onClick={commands.status}
            disabled={loading}
            className="action-btn status"
          >
            📊 Status
          </button>

          <button
            onClick={commands.taskList}
            disabled={loading}
            className="action-btn tasks"
          >
            📋 Task List
          </button>

          <button
            onClick={commands.qualityCheck}
            disabled={loading}
            className="action-btn quality"
          >
            ✅ Quality Check
          </button>

          <button
            onClick={commands.agentList}
            disabled={loading}
            className="action-btn agents"
          >
            🤖 Agent List
          </button>
        </div>

        {lastInitProject && (
          <div className="planning-prompt">
            <h4>Project "{lastInitProject}" Ready!</h4>
            <p>Start planning your project with Claude AI:</p>
            <button
              onClick={async () => {
                const result = await executeCommand('br plan');
                if (result && result.output) {
                  const planPrompt = `I'm starting a new project called "${lastInitProject}". Please help me plan and build this project using BuildRunner.\n\n${result.output}`;

                  if (isElectron && window.electronAPI) {
                    // Launch Claude directly in Electron
                    try {
                      await window.electronAPI.launchClaude(lastInitProject, planPrompt);
                      const msg: CommandResult = {
                        command: '🚀 Launched Claude Terminal',
                        output: 'A new Terminal window has been opened with Claude Code running your planning prompt!',
                        timestamp: new Date()
                      };
                      setHistory(prev => [...prev, msg]);
                    } catch (err) {
                      // Fallback to clipboard
                      navigator.clipboard.writeText(planPrompt).then(() => {
                        const msg: CommandResult = {
                          command: '📋 Copied to Clipboard',
                          output: 'Could not launch Claude directly. Planning prompt copied to clipboard!',
                          timestamp: new Date()
                        };
                        setHistory(prev => [...prev, msg]);
                      });
                    }
                  } else {
                    // Web browser - copy to clipboard
                    navigator.clipboard.writeText(planPrompt).then(() => {
                      const msg: CommandResult = {
                        command: '📋 Copied to Clipboard',
                        output: 'Planning prompt copied! Open Claude and paste to start planning.',
                        timestamp: new Date()
                      };
                      setHistory(prev => [...prev, msg]);
                    });
                  }
                }
              }}
              disabled={loading}
              className="action-btn plan-btn"
            >
              🧠 Start Planning Mode
            </button>
            <button
              onClick={() => executeCommand('br prd')}
              disabled={loading}
              className="action-btn prd-btn"
            >
              📄 Create PRD
            </button>
          </div>
        )}
      </div>

      <div className="terminal-container">
        <div className="terminal-header">
          <span>BuildRunner Terminal</span>
          <span className="path">{projectPath}</span>
        </div>

        <div className="terminal-output" ref={terminalRef}>
          {history.map((result, idx) => (
            <div key={idx} className="command-result">
              <div className="command-line">
                <span className="prompt">BR ❯</span>
                <span className="command-text">{result.command}</span>
              </div>
              {result.output && (
                <pre className="output">{result.output}</pre>
              )}
              {result.error && (
                <pre className="error">❌ {result.error}</pre>
              )}
            </div>
          ))}
          {loading && (
            <div className="loading">
              <span className="spinner">⏳</span> Executing command...
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="terminal-input">
          <span className="prompt">BR ❯</span>
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter any br command (e.g., br run, br quality check)"
            disabled={loading}
            className="command-input"
            autoFocus
          />
          <button type="submit" disabled={loading || !command.trim()} className="submit-btn">
            Execute
          </button>
        </form>
      </div>

      <div className="help-section">
        <h3>Available Commands</h3>
        <div className="command-grid">
          <div className="command-item">
            <code>br init [name]</code> - Initialize new project
          </div>
          <div className="command-item">
            <code>br run</code> - Run the build
          </div>
          <div className="command-item">
            <code>br status</code> - Check status
          </div>
          <div className="command-item">
            <code>br task list</code> - List all tasks
          </div>
          <div className="command-item">
            <code>br quality check</code> - Run quality checks
          </div>
          <div className="command-item">
            <code>br agent list</code> - List AI agents
          </div>
          <div className="command-item">
            <code>br plan</code> - Start planning mode
          </div>
          <div className="command-item">
            <code>br quality lint</code> - Run linter
          </div>
          <div className="command-item">
            <code>br quality typecheck</code> - Type check
          </div>
          <div className="command-item">
            <code>br test</code> - Run tests
          </div>
          <div className="command-item">
            <code>br validate</code> - Validate project
          </div>
          <div className="command-item">
            <code>br generate</code> - Generate code
          </div>
        </div>
      </div>
    </div>
  );
}