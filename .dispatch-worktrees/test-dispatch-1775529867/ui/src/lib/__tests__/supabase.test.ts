import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock supabaseLogger to capture calls without hitting the network
vi.mock('../supabaseLogger', () => ({
  logOperation: vi.fn(),
  logEvent: vi.fn(),
}));

// Mock @supabase/supabase-js
const mockOnAuthStateChange = vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } });
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn((_url: string, _key: string, opts?: Record<string, unknown>) => {
    // Store the custom fetch so tests can inspect it
    const globalOpts = opts?.global as { fetch?: typeof globalThis.fetch } | undefined;
    return {
      _customFetch: globalOpts?.fetch ?? null,
      auth: { onAuthStateChange: mockOnAuthStateChange },
    };
  }),
}));

describe('supabase client', () => {
  beforeEach(() => {
    vi.resetModules();
    // Set env vars for each test
    vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates a Supabase client with instrumented fetch in dev mode', async () => {
    const { getSupabaseClient } = await import('../supabase');
    const client = getSupabaseClient() as unknown as { _customFetch: typeof globalThis.fetch | null };

    // In dev mode (vitest runs with DEV=true), should have custom fetch
    expect(client._customFetch).not.toBeNull();
  });

  it('registers auth state change listener in dev mode', async () => {
    const { getSupabaseClient } = await import('../supabase');
    getSupabaseClient();

    expect(mockOnAuthStateChange).toHaveBeenCalledOnce();
  });

  it('returns same client instance on subsequent calls', async () => {
    const { getSupabaseClient } = await import('../supabase');
    const first = getSupabaseClient();
    const second = getSupabaseClient();

    expect(first).toBe(second);
  });

  it('logRealtimeEvent logs table and event type', async () => {
    const { logEvent } = await import('../supabaseLogger');
    const { logRealtimeEvent } = await import('../supabase');

    logRealtimeEvent({ table: 'messages', eventType: 'INSERT' });

    expect(logEvent).toHaveBeenCalledWith('REALTIME', 'INSERT on messages');
  });

  it('logRealtimeEvent handles missing fields gracefully', async () => {
    const { logEvent } = await import('../supabaseLogger');
    const { logRealtimeEvent } = await import('../supabase');

    logRealtimeEvent({});

    expect(logEvent).toHaveBeenCalledWith('REALTIME', 'unknown on unknown');
  });
});

describe('instrumented fetch wrapper', () => {
  let mockOriginalFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'test-anon-key');

    mockOriginalFetch = vi.fn().mockResolvedValue(
      new Response('{"data":[{"id":1}]}', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', mockOriginalFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('logs operation details for Supabase requests', async () => {
    const { logOperation } = await import('../supabaseLogger');
    const { getSupabaseClient } = await import('../supabase');
    const client = getSupabaseClient() as unknown as { _customFetch: typeof globalThis.fetch };

    if (client._customFetch) {
      await client._customFetch('https://test.supabase.co/rest/v1/users?select=*', {
        method: 'GET',
      });

      expect(logOperation).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'GET',
          url: 'https://test.supabase.co/rest/v1/users?select=*',
          status: 200,
        })
      );
    }
  });

  it('passes through non-Supabase requests without logging', async () => {
    const { logOperation } = await import('../supabaseLogger');
    const { getSupabaseClient } = await import('../supabase');
    const client = getSupabaseClient() as unknown as { _customFetch: typeof globalThis.fetch };

    if (client._customFetch) {
      await client._customFetch('https://other-api.com/data', { method: 'GET' });

      expect(logOperation).not.toHaveBeenCalled();
    }
  });

  it('captures response size and duration', async () => {
    const { logOperation } = await import('../supabaseLogger');
    const { getSupabaseClient } = await import('../supabase');
    const client = getSupabaseClient() as unknown as { _customFetch: typeof globalThis.fetch };

    if (client._customFetch) {
      await client._customFetch('https://test.supabase.co/rest/v1/items', {
        method: 'POST',
      });

      expect(logOperation).toHaveBeenCalledWith(
        expect.objectContaining({
          durationMs: expect.any(Number),
          responseSize: expect.any(Number),
        })
      );
    }
  });
});
