import { test, expect } from '@playwright/test';

test.describe('API Health Check', () => {
  test('should have healthy backend API', async ({ request }) => {
    const response = await request.get('http://localhost:8080/health');
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('should return API version info', async ({ request }) => {
    const response = await request.get('http://localhost:8080/health');
    const body = await response.json();

    expect(body).toHaveProperty('version');
    expect(body).toHaveProperty('timestamp');
  });

  test('should have CORS headers configured', async ({ request }) => {
    const response = await request.options('http://localhost:8080/api/orchestrator/status');

    const headers = response.headers();
    expect(headers['access-control-allow-origin']).toBe('http://localhost:5173');
    expect(headers['access-control-allow-methods']).toContain('GET');
    expect(headers['access-control-allow-methods']).toContain('POST');
  });

  test('should authenticate with valid JWT token', async ({ request }) => {
    // Login to get token
    const loginResponse = await request.post('http://localhost:8080/api/auth/login', {
      data: {
        email: 'admin@buildrunner.local',
        password: 'admin'
      }
    });

    expect(loginResponse.ok()).toBeTruthy();
    const loginBody = await loginResponse.json();
    expect(loginBody).toHaveProperty('token');

    const token = loginBody.token;

    // Use token to access protected endpoint
    const protectedResponse = await request.get('http://localhost:8080/api/orchestrator/status', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    expect(protectedResponse.ok()).toBeTruthy();
  });
});
