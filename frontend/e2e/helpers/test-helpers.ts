/**
 * Shared helper functions for Playwright E2E tests.
 */

import { Page, expect } from '@playwright/test';

/**
 * Login helper function.
 * In dev mode, the app auto-authenticates, so we just navigate to the app.
 *
 * @param page - Playwright Page object
 * @param email - User email (from E2E_TEST_EMAIL env var, defaults to dev@example.com for dev mode)
 * @param password - User password (from E2E_TEST_PASSWORD env var, defaults to password for dev mode)
 */
export async function login(
  page: Page,
  email = process.env.E2E_TEST_EMAIL || 'dev@example.com',
  password = process.env.E2E_TEST_PASSWORD || 'password'
) {
  // Navigate to dashboard - app will auto-authenticate in dev mode
  await page.goto('/dashboard');

  // If we're redirected to login page, fill the form
  const url = page.url();
  if (url.includes('/login')) {
    // Fill login form
    await page.fill('input[name="email"]', email);
    await page.fill('input[type="password"]', password);

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for navigation to complete
    await page.waitForURL(/\/(dashboard|profile|configuration)/, { timeout: 10000 });
  } else {
    // Already authenticated, wait for page to stabilize
    await page.waitForLoadState('networkidle');
  }
}

/**
 * Login as admin helper function.
 */
export async function loginAsAdmin(page: Page) {
  await login(
    page,
    process.env.E2E_TEST_ADMIN_EMAIL || 'admin@example.com',
    process.env.E2E_TEST_ADMIN_PASSWORD || 'admin123'
  );
}

/**
 * Navigate to User Profile -> AI Preferences tab.
 */
export async function goToAIPreferences(page: Page) {
  await page.goto('/profile');

  // Click "AI Preferences" tab
  await page.click('button:has-text("AI Preferences"), text=AI Preferences');

  // Wait for content to load
  await expect(page.locator('text=Prompt Templates, text=LLM Parameters').first()).toBeVisible({ timeout: 10000 });
}

/**
 * Navigate to System Configuration -> Operational Overrides tab.
 */
export async function goToOperationalOverrides(page: Page) {
  await page.goto('/configuration');

  // Click "Operational Overrides" tab
  await page.click('button:has-text("Operational Overrides")');

  // Wait for content to load
  await expect(page.locator('text=Operational Overrides').first()).toBeVisible({ timeout: 10000 });
}

/**
 * Wait for API response with timeout.
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  method?: string,
  timeout = 10000
) {
  return page.waitForResponse(
    (response) => {
      const matchesUrl = typeof urlPattern === 'string'
        ? response.url().includes(urlPattern)
        : urlPattern.test(response.url());
      const matchesMethod = method ? response.request().method() === method : true;
      return matchesUrl && matchesMethod;
    },
    { timeout }
  );
}

/**
 * Create a test prompt template.
 */
export async function createTestPromptTemplate(
  page: Page,
  name: string,
  type: 'RAG_QUERY' | 'QUESTION_GENERATION' | 'CUSTOM' = 'CUSTOM',
  templateFormat = 'Answer: {question}'
) {
  // Assumes we're already on the Manage Templates page
  await page.click('button:has-text("Create"), button:has-text("New Template")');
  await page.waitForTimeout(500);

  await page.fill('input[name="name"], input[placeholder*="name" i]', name);
  await page.selectOption('select[name="template_type"], select[name="type"]', type);
  await page.fill('textarea[name="template_format"], textarea[placeholder*="template" i]', templateFormat);

  await page.click('button[type="submit"], button:has-text("Create Template")');
  await page.waitForTimeout(1000);
}

/**
 * Create a test runtime config override.
 */
export async function createTestOverride(
  page: Page,
  configKey: string,
  value: any = true,
  valueType: 'str' | 'int' | 'float' | 'bool' | 'list' | 'dict' = 'bool',
  scope: 'GLOBAL' | 'USER' | 'COLLECTION' = 'GLOBAL',
  category: 'SYSTEM' | 'OVERRIDE' | 'EXPERIMENT' | 'PERFORMANCE' = 'SYSTEM'
) {
  // Assumes we're already on Operational Overrides page
  await page.click('button:has-text("Create Override")');
  await page.waitForTimeout(500);

  await page.selectOption('select', { label: scope });
  await page.selectOption('select', { label: category });
  await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', configKey);

  // Select value type
  const valueTypeLabel = valueType === 'str' ? 'String'
    : valueType === 'int' ? 'Integer'
    : valueType === 'float' ? 'Float'
    : valueType === 'bool' ? 'Boolean'
    : valueType === 'list' ? 'List'
    : 'Dictionary';

  await page.selectOption('select', { label: valueTypeLabel });

  // Fill value based on type
  if (valueType === 'bool') {
    await page.selectOption('select', { label: value ? 'True' : 'False' });
  } else {
    const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value);
    await page.fill('input[type="text"]:not([name*="key"]):not([name="scope"]):not([name="category"])', valueStr);
  }

  await page.click('button:has-text("Create Override")').last();
  await page.waitForTimeout(1000);
}

/**
 * Delete all test data (cleanup helper).
 */
export async function cleanupTestData(page: Page, pattern: string) {
  // Setup dialog handler
  page.on('dialog', dialog => dialog.accept());

  // Find all rows matching pattern
  const rows = page.locator(`text=${pattern}`);
  const count = await rows.count();

  for (let i = 0; i < count; i++) {
    const deleteButton = rows.nth(i).locator('..').locator('button[aria-label="Delete"], svg.w-4.h-4').first();
    if (await deleteButton.isVisible()) {
      await deleteButton.click();
      await page.waitForTimeout(500);
    }
  }
}
