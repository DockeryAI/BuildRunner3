/**
 * TelemetryTimeline Component
 *
 * Displays telemetry events in a timeline view
 */

import { useEffect, useState } from 'react';
import { telemetryAPI } from '../services/api';
import type { TelemetryEvent } from '../types';
import './TelemetryTimeline.css';

interface TelemetryTimelineProps {
  limit?: number;
  eventTypes?: string[];
}

export function TelemetryTimeline({ limit = 100, eventTypes }: TelemetryTimelineProps) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEvents();
    const interval = setInterval(loadEvents, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [limit, eventTypes]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const params: any = { limit };
      if (eventTypes && eventTypes.length > 0) {
        params.event_types = eventTypes.join(',');
      }

      const data = await telemetryAPI.getEvents(params);
      setEvents(data);
      setError(null);
    } catch (err) {
      setError('Failed to load telemetry events');
      console.error('Error loading events:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getEventTypeColor = (eventType: string): string => {
    if (eventType.includes('TASK_')) return '#0066cc';
    if (eventType.includes('BUILD_')) return '#9c27b0';
    if (eventType.includes('ERROR_')) return '#f44336';
    if (eventType.includes('PERFORMANCE_')) return '#ff9800';
    if (eventType.includes('MODEL_')) return '#4caf50';
    return '#888';
  };

  const getEventIcon = (eventType: string): string => {
    if (eventType.includes('STARTED')) return '▶';
    if (eventType.includes('COMPLETED')) return '✓';
    if (eventType.includes('FAILED')) return '✗';
    if (eventType.includes('ERROR')) return '⚠';
    if (eventType.includes('MODEL')) return '🤖';
    return '•';
  };

  if (loading && events.length === 0) {
    return <div className="timeline-loading">Loading events...</div>;
  }

  if (error) {
    return <div className="timeline-error">{error}</div>;
  }

  if (events.length === 0) {
    return <div className="timeline-empty">No events found</div>;
  }

  return (
    <div className="telemetry-timeline">
      <h2>Telemetry Timeline</h2>
      <div className="timeline-container">
        {events.map((event) => (
          <div key={event.event_id} className="timeline-event">
            <div
              className="event-marker"
              style={{ backgroundColor: getEventTypeColor(event.event_type) }}
            >
              {getEventIcon(event.event_type)}
            </div>
            <div className="event-content">
              <div className="event-header">
                <span
                  className="event-type"
                  style={{ color: getEventTypeColor(event.event_type) }}
                >
                  {event.event_type}
                </span>
                <span className="event-timestamp">
                  {formatTimestamp(event.timestamp)}
                </span>
              </div>
              {event.session_id && (
                <div className="event-session">Session: {event.session_id}</div>
              )}
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="event-metadata">
                  {Object.entries(event.metadata).map(([key, value]) => (
                    <div key={key} className="metadata-item">
                      <span className="metadata-key">{key}:</span>
                      <span className="metadata-value">
                        {typeof value === 'object'
                          ? JSON.stringify(value)
                          : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TelemetryTimeline;
