/**
 * AgentPool Component
 *
 * Displays agent pool status and active sessions
 */

import { useEffect, useState } from 'react';
import { agentsAPI } from '../services/api';
import type { AgentPoolStatus, Session } from '../types';
import './AgentPool.css';

export function AgentPool() {
  const [poolStatus, setPoolStatus] = useState<AgentPoolStatus | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000); // Refresh every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [pool, activeSessions] = await Promise.all([
        agentsAPI.getPool(),
        agentsAPI.getActiveSessions(),
      ]);
      setPoolStatus(pool);
      setSessions(activeSessions);
      setError(null);
    } catch (err) {
      setError('Failed to load agent pool data');
      console.error('Error loading agent pool:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      created: '#888',
      running: '#ff9800',
      paused: '#0066cc',
      completed: '#4caf50',
      failed: '#f44336',
      cancelled: '#607d8b',
    };
    return colors[status] || '#888';
  };

  if (loading && !poolStatus) {
    return <div className="agent-pool-loading">Loading agent pool...</div>;
  }

  if (error) {
    return <div className="agent-pool-error">{error}</div>;
  }

  if (!poolStatus) {
    return <div className="agent-pool-empty">No agent pool data</div>;
  }

  const utilizationPercent =
    poolStatus.max_concurrent > 0
      ? (poolStatus.active_sessions / poolStatus.max_concurrent) * 100
      : 0;

  return (
    <div className="agent-pool">
      <h2>Agent Pool</h2>

      <div className="pool-stats">
        <div className="stat-card">
          <div className="stat-value">{poolStatus.active_sessions}</div>
          <div className="stat-label">Active</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{poolStatus.available_slots}</div>
          <div className="stat-label">Available</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{poolStatus.max_concurrent}</div>
          <div className="stat-label">Capacity</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{utilizationPercent.toFixed(0)}%</div>
          <div className="stat-label">Utilization</div>
        </div>
      </div>

      <div className="utilization-bar">
        <div
          className="utilization-fill"
          style={{ width: `${utilizationPercent}%` }}
        />
      </div>

      <div className="pool-summary">
        <div className="summary-item">
          <span>Total Sessions:</span>
          <strong>{poolStatus.total_sessions}</strong>
        </div>
        <div className="summary-item">
          <span>Completed:</span>
          <strong>{poolStatus.completed_sessions}</strong>
        </div>
        <div className="summary-item">
          <span>Failed:</span>
          <strong>{poolStatus.failed_sessions}</strong>
        </div>
        <div className="summary-item">
          <span>Paused:</span>
          <strong>{poolStatus.paused_sessions}</strong>
        </div>
      </div>

      {sessions.length > 0 && (
        <div className="active-sessions">
          <h3>Active Sessions</h3>
          <div className="session-list">
            {sessions.map((session) => (
              <div key={session.session_id} className="session-item">
                <div className="session-header">
                  <span
                    className="session-status"
                    style={{ backgroundColor: getStatusColor(session.status) }}
                  >
                    {session.status}
                  </span>
                  <span className="session-name">{session.name}</span>
                </div>
                <div className="session-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${session.progress_percent}%` }}
                    />
                  </div>
                  <span className="progress-text">
                    {session.progress_percent.toFixed(0)}%
                  </span>
                </div>
                <div className="session-stats">
                  <span>
                    {session.completed_tasks}/{session.total_tasks} tasks
                  </span>
                  {session.failed_tasks > 0 && (
                    <span className="failed-count">
                      {session.failed_tasks} failed
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentPool;
