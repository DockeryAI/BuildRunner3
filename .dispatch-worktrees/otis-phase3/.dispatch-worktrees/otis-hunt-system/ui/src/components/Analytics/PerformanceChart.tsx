import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import './Analytics.css';

interface PerformanceMetric {
  agent_id: string;
  success_rate: number;
  total_tasks: number;
  successful_tasks: number;
  failed_tasks: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  p99_duration_ms: number;
  total_cost_usd: number;
  avg_cost_per_task: number;
  timestamp: string;
}

interface PerformanceChartProps {
  period?: 'hour' | 'day' | 'week' | 'all';
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ period = 'day' }) => {
  const [data, setData] = useState<PerformanceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/agent-performance?period=${period}`);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const metrics = await response.json();
        setData(metrics);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch performance data');
        setData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);

  if (loading) {
    return <div className="analytics-container loading">Loading performance data...</div>;
  }

  if (error) {
    return <div className="analytics-container error">Error: {error}</div>;
  }

  if (!data || data.length === 0) {
    return <div className="analytics-container empty">No performance data available</div>;
  }

  const metric = data[0];

  // Prepare chart data for success rate trend (simulated)
  const chartData = [
    {
      name: 'Success Rate',
      value: metric.success_rate,
      rate: metric.success_rate,
    },
  ];

  // Performance metrics summary
  const performanceStats = [
    { label: 'Success Rate', value: `${metric.success_rate.toFixed(2)}%`, highlight: true },
    { label: 'Total Tasks', value: metric.total_tasks },
    { label: 'Successful', value: metric.successful_tasks },
    { label: 'Failed', value: metric.failed_tasks },
    { label: 'Avg Duration', value: `${metric.avg_duration_ms.toFixed(0)}ms` },
    { label: 'P95 Duration', value: `${metric.p95_duration_ms.toFixed(0)}ms` },
    { label: 'P99 Duration', value: `${metric.p99_duration_ms.toFixed(0)}ms` },
    { label: 'Cost/Task', value: `$${metric.avg_cost_per_task.toFixed(4)}` },
  ];

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h2>Agent Performance Metrics</h2>
        <span className="period-badge">{period}</span>
      </div>

      <div className="metrics-grid">
        {performanceStats.map((stat, idx) => (
          <div key={idx} className={`metric-card ${stat.highlight ? 'highlight' : ''}`}>
            <div className="metric-label">{stat.label}</div>
            <div className="metric-value">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="chart-container">
        <h3>Success Rate Overview</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="rate" fill="#10b981" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="metrics-details">
        <h3>Detailed Metrics</h3>
        <div className="details-table">
          <div className="table-row header">
            <div className="table-cell">Metric</div>
            <div className="table-cell">Value</div>
          </div>
          {performanceStats.map((stat, idx) => (
            <div key={idx} className="table-row">
              <div className="table-cell">{stat.label}</div>
              <div className="table-cell">{stat.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PerformanceChart;
