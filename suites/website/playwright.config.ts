import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const baseURL = process.env.WEBSITE_BASE_URL || 'http://127.0.0.1:3000';
const profile = process.env.E2E_TARGET || 'local';
const reportsDir =
  process.env.E2E_REPORTS_DIR || path.join(__dirname, '..', '..', 'reports', profile);

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(reportsDir, 'playwright-website'), open: 'never' }],
    ['junit', { outputFile: path.join(reportsDir, 'website-junit.xml') }],
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
