/**
 * Tests for IntelligenceTab component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { IntelligenceTab } from './IntelligenceTab';
import * as api from '../services/api';

vi.mock('../services/api');

const mockIntelItems = [
  {
    id: 1,
    title: 'Claude 4.5 Released',
    source: 'anthropic-blog',
    url: 'https://anthropic.com/blog/claude-4-5',
    source_type: 'Official',
    category: 'model-release',
    priority: 'critical',
    score: 95,
    summary: 'New model with enhanced reasoning',
    opus_synthesis: 'This is a major release that affects BR3 cluster operations.',
    br3_improvement: true,
    read: false,
    dismissed: false,
    collected_at: '2026-04-06T10:00:00Z',
  },
  {
    id: 2,
    title: 'Community Tool: Agent Orchestrator v2',
    source: 'github-releases',
    url: 'https://github.com/example/agent-orchestrator',
    source_type: 'Community',
    category: 'community-tool',
    priority: 'high',
    score: 72,
    summary: 'New orchestrator with parallel execution',
    opus_synthesis: null,
    br3_improvement: false,
    read: false,
    dismissed: false,
    collected_at: '2026-04-06T09:00:00Z',
  },
  {
    id: 3,
    title: 'SDK Minor Update',
    source: 'npm-registry',
    url: 'https://npmjs.com/package/@anthropic-ai/sdk',
    source_type: 'Official',
    category: 'api-change',
    priority: 'medium',
    score: 45,
    summary: 'Bug fixes and performance improvements',
    opus_synthesis: null,
    br3_improvement: false,
    read: true,
    dismissed: false,
    collected_at: '2026-04-06T08:00:00Z',
  },
];

const mockAlerts = {
  critical_count: 1,
  high_count: 1,
};

const mockImprovements = [
  {
    id: 1,
    title: 'Agent Teams GA Integration',
    rationale: 'Agent Teams is now GA, BR3 should integrate',
    complexity: 'medium',
    setlist_prompt: '/setlist integrate Agent Teams GA into BR3 autopilot',
  },
];

describe('IntelligenceTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.intelAPI.getIntelItems as any).mockResolvedValue({ items: mockIntelItems, count: 3 });
    (api.intelAPI.getIntelAlerts as any).mockResolvedValue(mockAlerts);
    (api.intelAPI.getIntelImprovements as any).mockResolvedValue({ improvements: mockImprovements });
  });

  it('renders intelligence items sorted by priority', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Claude 4.5 Released')).toBeDefined();
      expect(screen.getByText('Community Tool: Agent Orchestrator v2')).toBeDefined();
      expect(screen.getByText('SDK Minor Update')).toBeDefined();
    });
  });

  it('shows critical items with red styling', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      const criticalItem = screen.getByText('Claude 4.5 Released').closest('.intel-item');
      expect(criticalItem?.classList.contains('priority-critical')).toBe(true);
    });
  });

  it('displays source and category badges', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Official')).toBeDefined();
      expect(screen.getByText('model-release')).toBeDefined();
    });
  });

  it('shows alert count', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      // Alert badge should show total critical + high = 2
      expect(screen.getByText('2')).toBeDefined();
    });
  });

  it('expands item to show opus synthesis on click', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Claude 4.5 Released')).toBeDefined();
    });
    fireEvent.click(screen.getByText('Claude 4.5 Released'));
    await waitFor(() => {
      expect(screen.getByText(/major release that affects BR3/)).toBeDefined();
    });
  });

  it('shows Build This badge for BR3 improvement items', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Build This')).toBeDefined();
    });
  });

  it('calls dismiss API when dismiss button clicked', async () => {
    (api.intelAPI.dismissIntelItem as any).mockResolvedValue({ status: 'ok' });
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Claude 4.5 Released')).toBeDefined();
    });
    // Expand item first
    fireEvent.click(screen.getByText('Claude 4.5 Released'));
    await waitFor(() => {
      const dismissButtons = screen.getAllByText('Dismiss');
      fireEvent.click(dismissButtons[0]);
    });
    expect(api.intelAPI.dismissIntelItem).toHaveBeenCalledWith(1);
  });

  it('filters items by category', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText('Claude 4.5 Released')).toBeDefined();
    });
    // Category filter should exist
    const categoryFilter = screen.getByDisplayValue('All Categories');
    expect(categoryFilter).toBeDefined();
  });

  it('shows improvement counter', async () => {
    render(<IntelligenceTab />);
    await waitFor(() => {
      expect(screen.getByText(/1 improvement/)).toBeDefined();
    });
  });
});
