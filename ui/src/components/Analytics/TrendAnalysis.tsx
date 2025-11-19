import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import './Analytics.css';

interface TrendPoint {
  timestamp: string;
  success_rate: number;
  total_tasks: number;
  successful_tasks: number;
  failed_tasks: number;
}

interface SuccessTrendsResponse {
  period: string;
  start_date: string;
  end_date: string;
  points: TrendPoint[];
  avg_success_rate: number;
  min_success_rate: number;
  max_success_rate: number;
}

interface TrendAnalysisProps {
  period?: 'hour' | 'day' | 'week';
  days?: number;
}

export const TrendAnalysis: React.FC<TrendAnalysisProps> = ({ period = 'day', days = 7 }) => {
  const [data, setData] = useState<SuccessTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `/api/analytics/success-trends?period=${period}&days=${days}`
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const trendData = await response.json();
        setData(trendData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch trend data');
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period, days]);

  if (loading) {
    return <div className="analytics-container loading">Loading trend analysis...</div>;
  }

  if (error) {
    return <div className="analytics-container error">Error: {error}</div>;
  }

  if (!data || !data.points || data.points.length === 0) {
    return <div className="analytics-container empty">No trend data available</div>;
  }

  const trendStats = [
    {
      label: 'Average Success Rate',
      value: `${data.avg_success_rate.toFixed(2)}%`,
      highlight: true,
    },
    { label: 'Highest Success Rate', value: `${data.max_success_rate.toFixed(2)}%` },
    { label: 'Lowest Success Rate', value: `${data.min_success_rate.toFixed(2)}%` },
    { label: 'Period', value: `${data.start_date} to ${data.end_date}` },
  ];

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h2>Success Rate Trends</h2>
        <span className="period-badge">{data.period}</span>
      </div>

      <div className="metrics-grid">
        {trendStats.map((stat, idx) => (
          <div key={idx} className={`metric-card ${stat.highlight ? 'highlight' : ''}`}>
            <div className="metric-label">{stat.label}</div>
            <div className="metric-value">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="chart-container">
        <h3>Success Rate Trend Over Time</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data.points} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 12 }}
            />
            <YAxis label={{ value: 'Success Rate (%)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
            <Legend />
            <Line
              type="monotone"
              dataKey="success_rate"
              stroke="#10b981"
              dot={{ fill: '#10b981' }}
              strokeWidth={2}
              name="Success Rate"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-container">
        <h3>Task Counts Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.points} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 12 }}
            />
            <YAxis label={{ value: 'Task Count', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="total_tasks"
              stroke="#3b82f6"
              dot={{ fill: '#3b82f6' }}
              strokeWidth={2}
              name="Total Tasks"
            />
            <Line
              type="monotone"
              dataKey="successful_tasks"
              stroke="#10b981"
              dot={{ fill: '#10b981' }}
              strokeWidth={2}
              name="Successful"
            />
            <Line
              type="monotone"
              dataKey="failed_tasks"
              stroke="#ef4444"
              dot={{ fill: '#ef4444' }}
              strokeWidth={2}
              name="Failed"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="metrics-details">
        <h3>Daily Breakdown</h3>
        <div className="details-table">
          <div className="table-row header">
            <div className="table-cell">Date</div>
            <div className="table-cell">Success Rate</div>
            <div className="table-cell">Total Tasks</div>
            <div className="table-cell">Successful</div>
            <div className="table-cell">Failed</div>
          </div>
          {data.points.map((point, idx) => (
            <div key={idx} className="table-row">
              <div className="table-cell">{point.timestamp}</div>
              <div className="table-cell">{point.success_rate.toFixed(2)}%</div>
              <div className="table-cell">{point.total_tasks}</div>
              <div className="table-cell">{point.successful_tasks}</div>
              <div className="table-cell">{point.failed_tasks}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="export-section">
        <h3>Export Options</h3>
        <button className="export-button pdf">
          <span>📄</span> Export as PDF
        </button>
        <button className="export-button csv">
          <span>📊</span> Export as CSV
        </button>
      </div>
    </div>
  );
};

export default TrendAnalysis;
