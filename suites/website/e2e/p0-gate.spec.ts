import { test, expect } from '@playwright/test';

/**
 * P0 black-box specs — hit WEBSITE_BASE_URL only (no route mocks).
 */

test.describe('P0 marketing gate @p0', () => {
  test('homepage loads with visible h1 @p0', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('primary navigation reaches use cases @p0', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /use cases/i }).first().click();
    await expect(page).toHaveURL(/use-cases/);
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('cookie banner accept flow @p0', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByRole('dialog', { name: /cookie choices/i })).toBeVisible();
    await page.getByRole('button', { name: /accept all/i }).click();
    await expect(page.getByRole('dialog', { name: /cookie choices/i })).not.toBeVisible();
    const consent = await page.evaluate(() => localStorage.getItem('cookie-consent'));
    expect(consent).toBe('all');
  });

  test('waitlist form is visible and accepts input @p0', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('cookie-consent', 'essential'));
    await page.reload();
    const form = page.locator('[data-testid="waitlist-form"]').first();
    await form.scrollIntoViewIfNeeded();
    await expect(form).toBeVisible();
    const email = form.locator('input[type="email"]').first();
    await expect(email).toBeVisible();
    await email.fill('e2e-p0@homecareguardian.test');
    await expect(email).toHaveValue('e2e-p0@homecareguardian.test');
  });
});
