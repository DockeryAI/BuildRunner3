/**
 * Dashboard Component
 *
 * Main dashboard view that combines all components
 */

import { useEffect, useState } from 'react';
import { orchestratorAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import type { OrchestratorStatus, Progress, WebSocketMessage } from '../types';
import { TaskList } from './TaskList';
import { AgentPool } from './AgentPool';
import { TelemetryTimeline } from './TelemetryTimeline';
import './Dashboard.css';

export function Dashboard() {
  const [status, setStatus] = useState<OrchestratorStatus | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'agents' | 'telemetry'>('tasks');
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket connection
  const { isConnected, lastMessage } = useWebSocket({
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onMessage: handleWebSocketMessage,
  });

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statusData, progressData] = await Promise.all([
        orchestratorAPI.getStatus(),
        orchestratorAPI.getProgress(),
      ]);
      setStatus(statusData);
      setProgress(progressData);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    }
  };

  function handleWebSocketMessage(message: WebSocketMessage) {
    // Handle different message types
    switch (message.type) {
      case 'task_update':
      case 'progress_update':
        loadDashboardData();
        break;
      case 'session_update':
        // Refresh agent pool if on that tab
        if (activeTab === 'agents') {
          // AgentPool component will auto-refresh
        }
        break;
    }
  }

  const handlePause = async () => {
    try {
      await orchestratorAPI.pause();
      loadDashboardData();
    } catch (err) {
      console.error('Error pausing orchestration:', err);
    }
  };

  const handleResume = async () => {
    try {
      await orchestratorAPI.resume();
      loadDashboardData();
    } catch (err) {
      console.error('Error resuming orchestration:', err);
    }
  };

  const handleStop = async () => {
    try {
      await orchestratorAPI.stop();
      loadDashboardData();
    } catch (err) {
      console.error('Error stopping orchestration:', err);
    }
  };

  const getStatusColor = (statusValue: string): string => {
    const colors: Record<string, string> = {
      idle: '#888',
      running: '#ff9800',
      paused: '#0066cc',
      completed: '#4caf50',
      failed: '#f44336',
    };
    return colors[statusValue] || '#888';
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>BuildRunner 3.2 Dashboard</h1>
        <div className="connection-status">
          <span className={`ws-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
          <span>{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </header>

      {status && progress && (
        <div className="dashboard-status">
          <div className="status-section">
            <div className="status-badge" style={{ backgroundColor: getStatusColor(status.status) }}>
              {status.status.toUpperCase()}
            </div>
            <div className="status-controls">
              {status.status === 'running' && (
                <>
                  <button onClick={handlePause} className="btn btn-secondary">
                    Pause
                  </button>
                  <button onClick={handleStop} className="btn btn-danger">
                    Stop
                  </button>
                </>
              )}
              {status.status === 'paused' && (
                <button onClick={handleResume} className="btn btn-primary">
                  Resume
                </button>
              )}
            </div>
          </div>

          <div className="progress-section">
            <div className="progress-stats">
              <div className="stat">
                <span className="stat-label">Total</span>
                <span className="stat-value">{progress.total}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Completed</span>
                <span className="stat-value completed">{progress.completed}</span>
              </div>
              <div className="stat">
                <span className="stat-label">In Progress</span>
                <span className="stat-value in-progress">{progress.in_progress}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Pending</span>
                <span className="stat-value pending">{progress.pending}</span>
              </div>
              {progress.failed > 0 && (
                <div className="stat">
                  <span className="stat-label">Failed</span>
                  <span className="stat-value failed">{progress.failed}</span>
                </div>
              )}
            </div>
            <div className="progress-bar-container">
              <div
                className="progress-bar-fill"
                style={{ width: `${progress.percent_complete}%` }}
              />
            </div>
            <div className="progress-percent">{progress.percent_complete.toFixed(1)}% Complete</div>
          </div>
        </div>
      )}

      <div className="dashboard-tabs">
        <button
          className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          Tasks
        </button>
        <button
          className={`tab ${activeTab === 'agents' ? 'active' : ''}`}
          onClick={() => setActiveTab('agents')}
        >
          Agent Pool
        </button>
        <button
          className={`tab ${activeTab === 'telemetry' ? 'active' : ''}`}
          onClick={() => setActiveTab('telemetry')}
        >
          Telemetry
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'tasks' && <TaskList />}
        {activeTab === 'agents' && <AgentPool />}
        {activeTab === 'telemetry' && <TelemetryTimeline />}
      </div>
    </div>
  );
}

export default Dashboard;
