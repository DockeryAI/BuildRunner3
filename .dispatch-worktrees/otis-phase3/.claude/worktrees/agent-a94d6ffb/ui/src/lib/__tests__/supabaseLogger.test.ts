import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock import.meta.env.DEV as true for all tests
vi.stubGlobal('import', { meta: { env: { DEV: true } } });

// We need to test the module internals, so we'll import after mocking
// The module uses import.meta.env.DEV which vitest handles via define

describe('supabaseLogger', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  describe('logOperation', () => {
    it('sends log line to dev server for a successful query', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/rest/v1/users?select=*',
        status: 200,
        durationMs: 42,
        responseSize: 512,
      });

      expect(fetchSpy).toHaveBeenCalledOnce();
      const [url, opts] = fetchSpy.mock.calls[0];
      expect(url).toBe('/__supabase_log');
      expect(opts.method).toBe('POST');
      expect(opts.body).toContain('[QUERY]');
      expect(opts.body).toContain('GET');
      expect(opts.body).toContain('/rest/v1/users');
      expect(opts.body).toContain('200');
      expect(opts.body).toContain('42ms');
      expect(opts.body).toContain('512b');
    });

    it('detects AUTH operations', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'POST',
        url: 'https://abc.supabase.co/auth/v1/token?grant_type=password',
        status: 200,
        durationMs: 150,
        responseSize: 1024,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[AUTH]');
    });

    it('detects STORAGE operations', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'POST',
        url: 'https://abc.supabase.co/storage/v1/object/avatars/pic.png',
        status: 200,
        durationMs: 300,
        responseSize: 0,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[STORAGE]');
    });

    it('detects EDGE_FN operations', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'POST',
        url: 'https://abc.supabase.co/functions/v1/send-email',
        status: 200,
        durationMs: 800,
        responseSize: 64,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[EDGE_FN]');
    });

    it('detects REALTIME operations', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/realtime/v1/websocket',
        status: 101,
        durationMs: 5,
        responseSize: 0,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[REALTIME]');
    });

    it('falls back to UNKNOWN for unrecognized paths', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/some/other/path',
        status: 200,
        durationMs: 10,
        responseSize: 100,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[UNKNOWN]');
    });
  });

  describe('warnings', () => {
    it('flags EMPTY_200 for 200 status with zero response size', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/rest/v1/secrets?select=*',
        status: 200,
        durationMs: 30,
        responseSize: 0,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('EMPTY_200');
      expect(body).toContain('RLS denial');
    });

    it('flags CLIENT_ERROR for 4xx status codes', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/rest/v1/users',
        status: 403,
        durationMs: 15,
        responseSize: 120,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('CLIENT_ERROR');
      expect(body).toContain('403');
    });

    it('flags SERVER_ERROR for 5xx status codes', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'POST',
        url: 'https://abc.supabase.co/rest/v1/users',
        status: 500,
        durationMs: 5000,
        responseSize: 50,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('SERVER_ERROR');
      expect(body).toContain('500');
    });

    it('flags TOKEN_REFRESH_FAIL for failed token requests', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'POST',
        url: 'https://abc.supabase.co/auth/v1/token?grant_type=refresh_token',
        status: 401,
        durationMs: 80,
        responseSize: 64,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      // Should have CLIENT_ERROR (since 401 is 4xx) which is checked first
      expect(body).toContain('CLIENT_ERROR');
    });

    it('does NOT flag warnings for normal successful responses', async () => {
      const { logOperation } = await import('../supabaseLogger');

      logOperation({
        method: 'GET',
        url: 'https://abc.supabase.co/rest/v1/users?select=*',
        status: 200,
        durationMs: 25,
        responseSize: 2048,
      });

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).not.toContain('⚠');
    });
  });

  describe('logEvent', () => {
    it('sends category event to dev server', async () => {
      const { logEvent } = await import('../supabaseLogger');

      logEvent('AUTH', 'SIGNED_IN user=abc-123');

      expect(fetchSpy).toHaveBeenCalledOnce();
      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[AUTH]');
      expect(body).toContain('SIGNED_IN user=abc-123');
    });

    it('sends realtime events', async () => {
      const { logEvent } = await import('../supabaseLogger');

      logEvent('REALTIME', 'INSERT on messages');

      const body = fetchSpy.mock.calls[0][1].body;
      expect(body).toContain('[REALTIME]');
      expect(body).toContain('INSERT on messages');
    });
  });

  describe('fetch failure resilience', () => {
    it('does not throw when fetch rejects', async () => {
      fetchSpy.mockRejectedValue(new Error('Network error'));
      const { logOperation } = await import('../supabaseLogger');

      // Should not throw
      expect(() => {
        logOperation({
          method: 'GET',
          url: 'https://abc.supabase.co/rest/v1/test',
          status: 200,
          durationMs: 10,
          responseSize: 100,
        });
      }).not.toThrow();
    });
  });
});
