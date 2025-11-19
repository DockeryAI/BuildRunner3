import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './Analytics.css';

interface CostBreakdownItem {
  name: string;
  cost_usd: number;
  percentage: number;
  token_count: number;
  task_count: number;
}

interface CostBreakdownResponse {
  total_cost_usd: number;
  period: string;
  breakdown_by_agent: CostBreakdownItem[];
  breakdown_by_model: CostBreakdownItem[];
  breakdown_by_type: CostBreakdownItem[];
}

interface CostBreakdownProps {
  period?: 'hour' | 'day' | 'week';
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export const CostBreakdown: React.FC<CostBreakdownProps> = ({ period = 'day' }) => {
  const [data, setData] = useState<CostBreakdownResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'agent' | 'model' | 'type'>('model');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/analytics/cost-breakdown?period=${period}`);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const costData = await response.json();
        setData(costData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch cost data');
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);

  if (loading) {
    return <div className="analytics-container loading">Loading cost breakdown...</div>;
  }

  if (error) {
    return <div className="analytics-container error">Error: {error}</div>;
  }

  if (!data) {
    return <div className="analytics-container empty">No cost data available</div>;
  }

  const getBreakdownData = () => {
    switch (activeTab) {
      case 'agent':
        return data.breakdown_by_agent;
      case 'model':
        return data.breakdown_by_model;
      case 'type':
        return data.breakdown_by_type;
      default:
        return data.breakdown_by_model;
    }
  };

  const breakdownData = getBreakdownData();

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h2>Cost Breakdown Visualization</h2>
        <div className="total-cost">
          Total Cost: <span className="cost-value">${data.total_cost_usd.toFixed(2)}</span>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'agent' ? 'active' : ''}`}
          onClick={() => setActiveTab('agent')}
        >
          By Agent
        </button>
        <button
          className={`tab-button ${activeTab === 'model' ? 'active' : ''}`}
          onClick={() => setActiveTab('model')}
        >
          By Model
        </button>
        <button
          className={`tab-button ${activeTab === 'type' ? 'active' : ''}`}
          onClick={() => setActiveTab('type')}
        >
          By Token Type
        </button>
      </div>

      <div className="chart-container">
        <h3>{activeTab === 'agent' ? 'Cost by Agent' : activeTab === 'model' ? 'Cost by Model' : 'Cost by Token Type'}</h3>

        {breakdownData && breakdownData.length > 0 ? (
          <>
            <div className="chart-row">
              <div className="chart-column">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={breakdownData}
                      dataKey="cost_usd"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                    >
                      {breakdownData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(4)}`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="chart-column">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={breakdownData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(value) => `$${Number(value).toFixed(4)}`} />
                    <Bar dataKey="cost_usd" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="breakdown-table">
              <div className="table-row header">
                <div className="table-cell">Name</div>
                <div className="table-cell">Cost</div>
                <div className="table-cell">Percentage</div>
                <div className="table-cell">Tokens</div>
                <div className="table-cell">Tasks</div>
              </div>
              {breakdownData.map((item, idx) => (
                <div key={idx} className="table-row">
                  <div className="table-cell">{item.name}</div>
                  <div className="table-cell">${item.cost_usd.toFixed(4)}</div>
                  <div className="table-cell">{item.percentage.toFixed(1)}%</div>
                  <div className="table-cell">{item.token_count}</div>
                  <div className="table-cell">{item.task_count}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state">No breakdown data available</div>
        )}
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

export default CostBreakdown;
