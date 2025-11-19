import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import { PerformanceChart } from './PerformanceChart';
import { CostBreakdown } from './CostBreakdown';
import { TrendAnalysis } from './TrendAnalysis';

// Mock recharts components
jest.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  Pie: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch as any;

describe('Analytics Components', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('PerformanceChart', () => {
    const mockPerformanceData = [
      {
        agent_id: 'aggregated',
        success_rate: 92.5,
        total_tasks: 100,
        successful_tasks: 92,
        failed_tasks: 8,
        avg_duration_ms: 1250.5,
        p95_duration_ms: 2100.0,
        p99_duration_ms: 2800.0,
        total_cost_usd: 15.75,
        avg_cost_per_task: 0.1575,
        timestamp: '2024-01-01T12:00:00Z',
      },
    ];

    it('should render loading state initially', () => {
      mockFetch.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<PerformanceChart period="day" />);

      expect(screen.getByText(/loading performance data/i)).toBeInTheDocument();
    });

    it('should render performance metrics after loading', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPerformanceData,
      });

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/agent performance metrics/i)).toBeInTheDocument();
      });

      // Check for metrics display
      expect(screen.getByText(/Success Rate/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Tasks/i)).toBeInTheDocument();
      expect(screen.getByText(/92.5%/)).toBeInTheDocument();
    });

    it('should handle API errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it('should display empty state when no data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(
          screen.getByText(/No performance data available/i)
        ).toBeInTheDocument();
      });
    });

    it('should fetch data with correct period parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPerformanceData,
      });

      render(<PerformanceChart period="week" />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/analytics/agent-performance')
        );
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('period=week')
        );
      });
    });

    it('should display all performance metrics', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPerformanceData,
      });

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Success Rate/i)).toBeInTheDocument();
        expect(screen.getByText(/Total Tasks/i)).toBeInTheDocument();
        expect(screen.getByText(/Successful/i)).toBeInTheDocument();
        expect(screen.getByText(/Failed/i)).toBeInTheDocument();
        expect(screen.getByText(/Avg Duration/i)).toBeInTheDocument();
        expect(screen.getByText(/P95 Duration/i)).toBeInTheDocument();
        expect(screen.getByText(/P99 Duration/i)).toBeInTheDocument();
        expect(screen.getByText(/Cost\/Task/i)).toBeInTheDocument();
      });
    });

    it('should format values correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPerformanceData,
      });

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(screen.getByText('92.5%')).toBeInTheDocument(); // success_rate
        expect(screen.getByText(/1250ms/)).toBeInTheDocument(); // avg_duration_ms
        expect(screen.getByText(/\$0.1575/)).toBeInTheDocument(); // avg_cost_per_task
      });
    });
  });

  describe('CostBreakdown', () => {
    const mockCostData = {
      total_cost_usd: 15.75,
      period: 'day',
      breakdown_by_agent: [
        {
          name: 'aggregated',
          cost_usd: 15.75,
          percentage: 100.0,
          token_count: 125000,
          task_count: 100,
        },
      ],
      breakdown_by_model: [
        {
          name: 'claude-3-sonnet',
          cost_usd: 9.45,
          percentage: 60.0,
          token_count: 75000,
          task_count: 60,
        },
        {
          name: 'claude-3-haiku',
          cost_usd: 6.3,
          percentage: 40.0,
          token_count: 50000,
          task_count: 40,
        },
      ],
      breakdown_by_type: [
        {
          name: 'input_tokens',
          cost_usd: 3.9375,
          percentage: 25.0,
          token_count: 37500,
          task_count: 100,
        },
        {
          name: 'output_tokens',
          cost_usd: 11.8125,
          percentage: 75.0,
          token_count: 87500,
          task_count: 100,
        },
      ],
    };

    it('should render loading state initially', () => {
      mockFetch.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<CostBreakdown period="day" />);

      expect(screen.getByText(/loading cost breakdown/i)).toBeInTheDocument();
    });

    it('should render cost breakdown after loading', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCostData,
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Cost Breakdown Visualization/i)).toBeInTheDocument();
        expect(screen.getByText(/Total Cost:/i)).toBeInTheDocument();
        expect(screen.getByText(/\$15.75/)).toBeInTheDocument();
      });
    });

    it('should have tabs for different breakdowns', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCostData,
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/By Agent/i)).toBeInTheDocument();
        expect(screen.getByText(/By Model/i)).toBeInTheDocument();
        expect(screen.getByText(/By Token Type/i)).toBeInTheDocument();
      });
    });

    it('should switch tabs on click', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCostData,
      });

      const user = userEvent.setup();
      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/By Model/i)).toBeInTheDocument();
      });

      const modelTab = screen.getByText(/By Model/i);
      await user.click(modelTab);

      // After clicking, the tab should show model breakdown
      await waitFor(() => {
        expect(screen.getByText(/Cost by Model/i)).toBeInTheDocument();
      });
    });

    it('should display breakdown table with correct headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCostData,
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Name/i)).toBeInTheDocument();
        expect(screen.getByText(/Cost/i)).toBeInTheDocument();
        expect(screen.getByText(/Percentage/i)).toBeInTheDocument();
        expect(screen.getByText(/Tokens/i)).toBeInTheDocument();
        expect(screen.getByText(/Tasks/i)).toBeInTheDocument();
      });
    });

    it('should render export buttons', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCostData,
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Export as PDF/i)).toBeInTheDocument();
        expect(screen.getByText(/Export as CSV/i)).toBeInTheDocument();
      });
    });

    it('should handle API errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });
  });

  describe('TrendAnalysis', () => {
    const mockTrendData = {
      period: 'day',
      start_date: '2024-01-01',
      end_date: '2024-01-07',
      points: [
        {
          timestamp: '2024-01-01',
          success_rate: 88.5,
          total_tasks: 100,
          successful_tasks: 88,
          failed_tasks: 12,
        },
        {
          timestamp: '2024-01-02',
          success_rate: 91.0,
          total_tasks: 110,
          successful_tasks: 100,
          failed_tasks: 10,
        },
        {
          timestamp: '2024-01-03',
          success_rate: 92.5,
          total_tasks: 120,
          successful_tasks: 111,
          failed_tasks: 9,
        },
      ],
      avg_success_rate: 90.67,
      min_success_rate: 88.5,
      max_success_rate: 92.5,
    };

    it('should render loading state initially', () => {
      mockFetch.mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<TrendAnalysis period="day" days={7} />);

      expect(screen.getByText(/loading trend analysis/i)).toBeInTheDocument();
    });

    it('should render trend analysis after loading', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Success Rate Trends/i)).toBeInTheDocument();
      });
    });

    it('should display trend statistics', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Average Success Rate/i)).toBeInTheDocument();
        expect(screen.getByText(/Highest Success Rate/i)).toBeInTheDocument();
        expect(screen.getByText(/Lowest Success Rate/i)).toBeInTheDocument();
        expect(screen.getByText(/90.67%/)).toBeInTheDocument();
      });
    });

    it('should render trend charts', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByTestId('line-chart')).toBeInTheDocument();
      });
    });

    it('should display daily breakdown table', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Daily Breakdown/i)).toBeInTheDocument();
        expect(screen.getByText(/Date/i)).toBeInTheDocument();
        expect(screen.getByText('2024-01-01')).toBeInTheDocument();
      });
    });

    it('should render export buttons', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Export as PDF/i)).toBeInTheDocument();
        expect(screen.getByText(/Export as CSV/i)).toBeInTheDocument();
      });
    });

    it('should fetch with correct parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrendData,
      });

      render(<TrendAnalysis period="week" days={14} />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/analytics/success-trends')
        );
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('period=week')
        );
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('days=14')
        );
      });
    });

    it('should handle empty trend data', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockTrendData,
          points: [],
        }),
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/No trend data available/i)).toBeInTheDocument();
      });
    });

    it('should handle API errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<PerformanceChart period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it('should handle malformed API responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      render(<CostBreakdown period="day" />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it('should handle HTTP errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      render(<TrendAnalysis period="day" days={7} />);

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });
  });

  describe('Component Integration', () => {
    it('should handle rapid period changes', async () => {
      const { rerender } = render(<PerformanceChart period="day" />);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            agent_id: 'aggregated',
            success_rate: 92.5,
            total_tasks: 100,
            successful_tasks: 92,
            failed_tasks: 8,
            avg_duration_ms: 1250.5,
            p95_duration_ms: 2100.0,
            p99_duration_ms: 2800.0,
            total_cost_usd: 15.75,
            avg_cost_per_task: 0.1575,
            timestamp: '2024-01-01T12:00:00Z',
          },
        ],
      });

      rerender(<PerformanceChart period="week" />);

      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
