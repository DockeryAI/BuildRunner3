/**
 * Log Viewer Component
 * Real-time log streaming from BuildRunner via WebSocket
 * Displays command output, errors, and status updates
 */

import React, { useState, useEffect, useRef } from 'react';
import './LogViewer.css';

const WS_URL = 'ws://localhost:8080/api/workspace/ws/logs';

interface LogEntry {
  type: string;
  file?: string;
  content?: string;
  command?: string;
  output?: string;
  error?: string;
  status?: string;
  details?: any;
  autodebug?: {
    overall_success: boolean;
    checks_run: number;
    critical_failures: number;
    duration_ms: number;
    report_file?: string;
  };
  timestamp: string;
}

interface LogViewerProps {
  projectName?: string;
  autoScroll?: boolean;
}

export function LogViewer({ projectName, autoScroll = true }: LogViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (autoScroll) {
      scrollToBottom();
    }
  }, [logs, autoScroll]);

  const connectWebSocket = () => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);

      // Send ping to keep alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);

      ws.addEventListener('close', () => {
        clearInterval(pingInterval);
      });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type !== 'pong') {
          addLogEntry(data);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);

      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        connectWebSocket();
      }, 5000);
    };

    wsRef.current = ws;
  };

  const addLogEntry = (entry: LogEntry) => {
    setLogs((prevLogs) => [...prevLogs, entry]);
  };

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const getFilteredLogs = () => {
    let filtered = logs;

    // Filter by type
    if (filter !== 'all') {
      filtered = filtered.filter((log) => {
        if (filter === 'errors') return log.type === 'command_output' && log.error;
        if (filter === 'commands') return log.type === 'command_output';
        if (filter === 'status') return log.type === 'status_update';
        if (filter === 'autodebug') return log.type === 'autodebug_report';
        if (filter === 'logs') return log.type === 'log_update' || log.type === 'initial_log';
        return true;
      });
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter((log) => {
        const searchableText = JSON.stringify(log).toLowerCase();
        return searchableText.includes(searchTerm.toLowerCase());
      });
    }

    // Filter by project name if specified
    if (projectName) {
      filtered = filtered.filter((log) => {
        if (log.file) return log.file.includes(projectName);
        if (log.command) return log.command.includes(projectName);
        return true;
      });
    }

    return filtered;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const getLogTypeClass = (log: LogEntry) => {
    if (log.error) return 'log-error';
    if (log.type === 'status_update') return 'log-status';
    if (log.type === 'command_output') return 'log-command';
    if (log.type === 'autodebug_report') {
      return log.autodebug?.overall_success ? 'log-autodebug-success' : 'log-autodebug-failure';
    }
    return 'log-info';
  };

  const renderLogContent = (log: LogEntry) => {
    switch (log.type) {
      case 'log_update':
      case 'initial_log':
        return (
          <div className="log-content">
            <div className="log-file">📄 {log.file}</div>
            <pre className="log-text">{log.content}</pre>
          </div>
        );

      case 'command_output':
        return (
          <div className="log-content">
            <div className="log-command">$ {log.command}</div>
            {log.output && <pre className="log-text">{log.output}</pre>}
            {log.error && <pre className="log-error-text">{log.error}</pre>}
          </div>
        );

      case 'status_update':
        return (
          <div className="log-content">
            <div className="log-status-text">
              🔔 Status: <strong>{log.status}</strong>
            </div>
            {log.details && (
              <pre className="log-details">{JSON.stringify(log.details, null, 2)}</pre>
            )}
          </div>
        );

      case 'autodebug_report':
        const autodebug = log.autodebug;
        if (!autodebug) return null;
        const statusIcon = autodebug.overall_success ? '✅' : '❌';
        const statusText = autodebug.overall_success ? 'PASSED' : 'FAILED';
        const statusClass = autodebug.overall_success ? 'autodebug-pass' : 'autodebug-fail';

        return (
          <div className="log-content autodebug-report">
            <div className={`autodebug-header ${statusClass}`}>
              <span className="autodebug-icon">{statusIcon}</span>
              <strong>Auto-Debug {statusText}</strong>
              <span className="autodebug-duration">({(autodebug.duration_ms / 1000).toFixed(1)}s)</span>
            </div>
            <div className="autodebug-stats">
              <div className="stat">
                <span className="stat-label">Checks Run:</span>
                <span className="stat-value">{autodebug.checks_run}</span>
              </div>
              {autodebug.critical_failures > 0 && (
                <div className="stat stat-error">
                  <span className="stat-label">Critical Failures:</span>
                  <span className="stat-value">{autodebug.critical_failures}</span>
                </div>
              )}
            </div>
            {autodebug.report_file && (
              <div className="autodebug-report-link">
                📄 Full report: {autodebug.report_file}
              </div>
            )}
          </div>
        );

      default:
        return (
          <div className="log-content">
            <pre className="log-text">{JSON.stringify(log, null, 2)}</pre>
          </div>
        );
    }
  };

  const filteredLogs = getFilteredLogs();

  return (
    <div className="log-viewer">
      <div className="log-header">
        <div className="log-title">
          <h3>📊 Build Logs</h3>
          <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '● Connected' : '○ Disconnected'}
          </div>
        </div>

        <div className="log-controls">
          <div className="log-filters">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Logs</option>
              <option value="logs">File Logs</option>
              <option value="commands">Commands</option>
              <option value="status">Status Updates</option>
              <option value="autodebug">Auto-Debug</option>
              <option value="errors">Errors Only</option>
            </select>

            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search logs..."
              className="search-input"
            />
          </div>

          <button onClick={clearLogs} className="clear-btn">
            🗑️ Clear
          </button>
        </div>
      </div>

      <div className="log-body">
        {filteredLogs.length === 0 ? (
          <div className="log-empty">
            {connected
              ? '📭 No logs yet. Waiting for BuildRunner output...'
              : '⚠️ Disconnected from log server. Reconnecting...'}
          </div>
        ) : (
          <div className="log-entries">
            {filteredLogs.map((log, index) => (
              <div key={index} className={`log-entry ${getLogTypeClass(log)}`}>
                <div className="log-timestamp">{formatTimestamp(log.timestamp)}</div>
                {renderLogContent(log)}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      <div className="log-footer">
        <span className="log-count">
          {filteredLogs.length} {filteredLogs.length === 1 ? 'entry' : 'entries'}
          {searchTerm && ` (filtered from ${logs.length})`}
        </span>
        <span className="auto-scroll-toggle">
          <label>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={() => {}}
              disabled
            />
            Auto-scroll
          </label>
        </span>
      </div>
    </div>
  );
}
