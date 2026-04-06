import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBuildStore } from '../stores/buildStore';
import { WebSocketClient } from '../utils/websocketClient';
import { ArchitectureCanvas } from '../components/ArchitectureCanvas';
import { TerminalPanel } from '../components/TerminalPanel';
import { ProgressSidebar } from '../components/ProgressSidebar';
import './BuildMonitor.css';

export const BuildMonitor: React.FC = () => {
  const { projectAlias } = useParams<{ projectAlias: string }>();
  const navigate = useNavigate();
  
  const { session, setSession, websocket, setWebSocketState, addTerminalLine, updateComponent, updateFeature } = useBuildStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  
  const wsClient = useRef<WebSocketClient | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!projectAlias) {
      setError('Project alias is required');
      setLoading(false);
      return;
    }

    // Fetch session data
    fetch(`http://localhost:8080/api/build/status/${projectAlias}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load build session: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setSession(data);
        setLoading(false);
        
        // Connect WebSocket
        if (!wsClient.current) {
          wsClient.current = new WebSocketClient();
          setupWebSocketHandlers(wsClient.current);
          wsClient.current.connect(data.id);
        }
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });

    // Cleanup
    return () => {
      if (wsClient.current) {
        wsClient.current.disconnect();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [projectAlias]);

  useEffect(() => {
    if (session && session.status === 'running') {
      timerRef.current = window.setInterval(() => {
        setElapsedTime(Date.now() - session.startTime);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [session?.status, session?.startTime]);

  const setupWebSocketHandlers = (ws: WebSocketClient) => {
    ws.on('connection', (data) => {
      setWebSocketState({ 
        connected: data.status === 'connected',
        reconnecting: data.status === 'reconnecting',
        error: null 
      });
    });

    ws.on('component_update', (data) => {
      if (data.component_id) {
        updateComponent(data.component_id, {
          status: data.status,
          progress: data.progress,
          files: data.files,
          error: data.error,
        });
      }
    });

    ws.on('feature_update', (data) => {
      if (data.feature_id) {
        updateFeature(data.feature_id, {
          status: data.status,
          progress: data.progress,
          tasks: data.tasks,
        });
      }
    });

    ws.on('terminal_output', (data) => {
      addTerminalLine({
        id: `${Date.now()}-${Math.random()}`,
        timestamp: data.timestamp || Date.now(),
        type: data.output_type || 'stdout',
        content: data.content || '',
      });
    });

    ws.on('build_progress', (data) => {
      if (session) {
        setSession({
          ...session,
          status: data.status || session.status,
          currentComponent: data.current_component,
          currentFeature: data.current_feature,
        });
      }
    });

    ws.on('error', (data) => {
      setWebSocketState({ error: data.message });
    });
  };

  const formatElapsedTime = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      initializing: '#3b82f6',
      running: '#10b981',
      paused: '#f59e0b',
      completed: '#22c55e',
      error: '#ef4444',
    };
    return colors[status] || '#6b7280';
  };

  if (loading) {
    return (
      <div className="build-monitor loading">
        <div className="loading-spinner"></div>
        <p>Loading build session...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="build-monitor error">
        <div className="error-container">
          <h2>Error Loading Build Session</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/')}>Go Back</button>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="build-monitor error">
        <div className="error-container">
          <h2>No Session Found</h2>
          <button onClick={() => navigate('/')}>Go Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="build-monitor">
      <header className="build-monitor-header">
        <div className="header-left">
          <h1>{session.projectName}</h1>
          <span className="project-alias">@{session.projectAlias}</span>
        </div>
        
        <div className="header-center">
          <div 
            className="status-indicator" 
            style={{ backgroundColor: getStatusColor(session.status) }}
          >
            {session.status}
          </div>
          <div className="elapsed-time">
            {formatElapsedTime(elapsedTime)}
          </div>
        </div>

        <div className="header-right">
          <div className={`ws-status ${websocket.connected ? 'connected' : websocket.reconnecting ? 'reconnecting' : 'disconnected'}`}>
            <span className="ws-dot"></span>
            {websocket.connected ? 'Connected' : websocket.reconnecting ? 'Reconnecting...' : 'Disconnected'}
          </div>
          {websocket.error && <div className="ws-error">{websocket.error}</div>}
        </div>
      </header>

      <div className="build-monitor-content">
        <div className="architecture-section">
          <ArchitectureCanvas 
            components={session.components}
            currentComponent={session.currentComponent}
          />
        </div>

        <aside className="progress-section">
          <ProgressSidebar 
            components={session.components}
            features={session.features}
          />
        </aside>
      </div>

      <div className="terminal-section">
        <TerminalPanel />
      </div>
    </div>
  );
};
