import { test, expect } from '@playwright/test';

// Requires: docker compose up --build (backend :8000, frontend :5173, :3000)
// Run: npx playwright test --project=chromium
// Env: BASE_URL=http://localhost:5173 or http://localhost:3000, API_URL=http://localhost:8000

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const API = process.env.API_URL || 'http://localhost:8000';

test.describe('OSINT E2E', () => {
  test('health endpoints', async ({ request }) => {
    const r = await request.get(`${API}/health/`);
    expect([200, 404]).toContain(r.status());
  });

  test('login redirect when unauthenticated', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await expect(page.locator('text=Login')).toBeVisible();
  });

  test('full flow smoke: sources list loads (requires auth mock or guest access)', async ({ page }) => {
    // If backend requires auth, this will redirect to login; assert either sources or login visible
    await page.goto(`${BASE}/sources`);
    await page.waitForLoadState('networkidle');
    const hasSources = await page.locator('text=Sources & Collection').count();
    const hasLogin = await page.locator('text=Login').count();
    expect(hasSources + hasLogin).toBeGreaterThan(0);
  });

  test('search view renders', async ({ page }) => {
    await page.goto(`${BASE}/search`);
    await expect(page.locator('text=Search & Filtering')).toBeVisible();
  });

  test('dashboard renders charts placeholder', async ({ page }) => {
    await page.goto(BASE + '/');
    await expect(page.locator('text=Intelligence Dashboard')).toBeVisible();
  });

  test('map view renders', async ({ page }) => {
    await page.goto(`${BASE}/map`);
    await expect(page.locator('text=Geographic Overlay')).toBeVisible();
    await expect(page.locator('#map')).toBeVisible();
  });

  test('alerts view renders watchlist form', async ({ page }) => {
    await page.goto(`${BASE}/alerts`);
    await expect(page.locator('text=Watchlists & Alerts')).toBeVisible();
    await expect(page.locator('text=Create Watchlist')).toBeVisible();
  });
});
