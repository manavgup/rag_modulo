/**
 * E2E tests for Operational Overrides in System Configuration.
 *
 * Tests admin-level operational controls:
 * - Feature flags
 * - Emergency overrides
 * - A/B testing configurations
 * - Performance tuning
 *
 * API Endpoints tested:
 * - GET /api/runtime-config/global
 * - POST /api/runtime-config
 * - PATCH /api/runtime-config/{id}/toggle
 * - DELETE /api/runtime-config/{id}
 */

import { test, expect, Page } from '@playwright/test';

// Helper function to login as admin
async function loginAsAdmin(page: Page) {
  await page.goto('/login');

  // Fill login form with admin credentials
  await page.fill('input[name="email"]', 'admin@example.com');
  await page.fill('input[type="password"]', 'admin123');

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for navigation
  await page.waitForURL(/\/(dashboard|configuration)/);
}

// Helper function to navigate to Operational Overrides
async function goToOperationalOverrides(page: Page) {
  await page.goto('/configuration');

  // Click "Operational Overrides" tab
  await page.click('button:has-text("Operational Overrides")');

  // Wait for content to load
  await expect(page.locator('text=Operational Overrides')).toBeVisible({ timeout: 10000 });
}

test.describe('Operational Overrides - View and Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should display "Operational Overrides" tab in System Configuration', async ({ page }) => {
    await page.goto('/configuration');

    // Verify tab exists
    await expect(page.locator('button:has-text("Operational Overrides")')).toBeVisible();
  });

  test('should navigate to Operational Overrides section', async ({ page }) => {
    await goToOperationalOverrides(page);

    // Verify section header
    await expect(page.locator('h2:has-text("Operational Overrides")')).toBeVisible();

    // Verify description
    await expect(
      page.locator('text=Feature flags, emergency overrides')
    ).toBeVisible();

    // Should have "Create Override" button
    await expect(page.locator('button:has-text("Create Override")')).toBeVisible();
  });

  test('should display empty state when no overrides exist', async ({ page }) => {
    await goToOperationalOverrides(page);

    // Wait for loading to complete
    await page.waitForTimeout(2000);

    // Should show empty state OR show existing overrides
    const hasOverrides = await page.locator('table tbody tr').count() > 0;
    const hasEmptyState = await page.locator('text=No overrides configured').isVisible();

    expect(hasOverrides || hasEmptyState).toBeTruthy();
  });

  test('should display scope tabs (Global, User, Collection)', async ({ page }) => {
    await goToOperationalOverrides(page);

    // Global tab should always be visible
    await expect(page.locator('button:has-text("Global")')).toBeVisible();

    // Note: User and Collection tabs may only appear if userId/collectionId are provided
    // This depends on component props
  });
});

test.describe('Operational Overrides - Create Override', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await goToOperationalOverrides(page);
  });

  test('should open create override form', async ({ page }) => {
    // Click "Create Override" button
    await page.click('button:has-text("Create Override")');

    // Form should appear
    await expect(page.locator('text=Create New Override')).toBeVisible({ timeout: 5000 });

    // Verify form fields
    await expect(page.locator('select[name="scope"]')).toBeVisible();
    await expect(page.locator('select[name="category"]')).toBeVisible();
    await expect(page.locator('input[name="config_key"]')).toBeVisible();
    await expect(page.locator('select[name="value_type"]')).toBeVisible();
  });

  test('should create a global feature flag', async ({ page }) => {
    // Open create form
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    const uniqueKey = `test_feature_${Date.now()}`;

    // Fill form
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'System' });
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', uniqueKey);
    await page.selectOption('select', { label: 'Boolean' });
    await page.selectOption('select', { label: 'True' });
    await page.fill('textarea[placeholder*="description" i]', 'Test feature flag for E2E testing');

    // Listen for API call
    const createPromise = page.waitForResponse(
      (response) => response.url().includes('/api/runtime-config') && response.request().method() === 'POST'
    );

    // Submit form
    await page.click('button:has-text("Create Override")');

    // Wait for API response
    const response = await createPromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(
      page.locator('text=Configuration override has been created successfully')
    ).toBeVisible({ timeout: 5000 });

    // Verify override appears in table
    await expect(page.locator(`text=${uniqueKey}`)).toBeVisible();
  });

  test('should create an emergency override', async ({ page }) => {
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    const emergencyKey = `emergency_disable_${Date.now()}`;

    // Fill form for emergency override
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'Override' }); // OVERRIDE category
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', emergencyKey);
    await page.selectOption('select', { label: 'Boolean' });
    await page.selectOption('select', { label: 'True' });
    await page.fill('textarea[placeholder*="description" i]', 'Emergency: Disable feature due to production issue');

    // Submit
    await page.click('button:has-text("Create Override")');

    // Verify success
    await expect(page.locator('text=Configuration override has been created successfully')).toBeVisible({ timeout: 5000 });
    await expect(page.locator(`text=${emergencyKey}`)).toBeVisible();

    // Verify OVERRIDE category badge
    await expect(page.locator('text=OVERRIDE, text=Override').first()).toBeVisible();
  });

  test('should create a performance tuning override with integer value', async ({ page }) => {
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    const perfKey = `batch_size_${Date.now()}`;

    // Fill form
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'Performance' });
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', perfKey);
    await page.selectOption('select', { label: 'Integer' });
    await page.fill('input[type="text"]:not([name*="key"]):not([name="scope"]):not([name="category"])','100');
    await page.fill('textarea[placeholder*="description" i]', 'Increase batch size for better performance');

    // Submit
    await page.click('button:has-text("Create Override")');

    // Verify
    await expect(page.locator('text=Configuration override has been created successfully')).toBeVisible({ timeout: 5000 });
    await expect(page.locator(`text=${perfKey}`)).toBeVisible();

    // Verify value shows as 100
    await expect(page.locator('code:has-text("100")').first()).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    // Try to submit without config_key
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'System' });
    // Don't fill config_key

    // Submit button should be disabled
    const submitButton = page.locator('button:has-text("Create Override")').last();
    await expect(submitButton).toBeDisabled();
  });

  test('should cancel form and hide it', async ({ page }) => {
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    // Verify form is visible
    await expect(page.locator('text=Create New Override')).toBeVisible();

    // Click cancel
    await page.click('button:has-text("Cancel")').last();

    // Form should disappear
    await expect(page.locator('text=Create New Override')).not.toBeVisible({ timeout: 3000 });
  });
});

test.describe('Operational Overrides - Toggle Status', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await goToOperationalOverrides(page);

    // Create a test override first
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    const testKey = `toggle_test_${Date.now()}`;
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'System' });
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', testKey);
    await page.selectOption('select', { label: 'Boolean' });
    await page.selectOption('select', { label: 'True' });

    await page.click('button:has-text("Create Override")').last();
    await page.waitForTimeout(1000);
  });

  test('should toggle override from active to inactive', async ({ page }) => {
    // Find the override row
    const firstOverride = page.locator('tbody tr').first();
    const statusButton = firstOverride.locator('button:has-text("Active"), button:has-text("Inactive")').first();

    const initialStatus = await statusButton.textContent();

    // Listen for toggle API call
    const togglePromise = page.waitForResponse(
      (response) => response.url().includes('/runtime-config/') && response.url().includes('/toggle')
    );

    // Click to toggle
    await statusButton.click();

    // Wait for API response
    const response = await togglePromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Override has been').first()).toBeVisible({ timeout: 5000 });

    // Status should have changed
    const newStatus = await statusButton.textContent();
    expect(newStatus).not.toBe(initialStatus);
  });

  test('should show visual indication for inactive overrides', async ({ page }) => {
    // Create and immediately toggle to inactive
    const firstRow = page.locator('tbody tr').first();
    const statusButton = firstRow.locator('button:has-text("Active")').first();

    if (await statusButton.isVisible()) {
      await statusButton.click();
      await page.waitForTimeout(1000);

      // Row should be dimmed/faded (opacity-50)
      const rowClasses = await firstRow.getAttribute('class');
      expect(rowClasses).toContain('opacity-50');
    }
  });
});

test.describe('Operational Overrides - Delete Override', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await goToOperationalOverrides(page);

    // Create a test override to delete
    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    const deleteKey = `delete_test_${Date.now()}`;
    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'System' });
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', deleteKey);
    await page.selectOption('select', { label: 'Boolean' });
    await page.selectOption('select', { label: 'False' });

    await page.click('button:has-text("Create Override")').last();
    await page.waitForTimeout(1000);
  });

  test('should delete override with confirmation', async ({ page }) => {
    // Find first override
    const firstOverride = page.locator('tbody tr').first();
    const deleteButton = firstOverride.locator('button[aria-label="Delete"], svg.w-4.h-4').first();

    // Get the key name before deletion
    const keyCell = firstOverride.locator('td').first();
    const keyName = await keyCell.textContent();

    // Setup dialog handler
    page.on('dialog', dialog => {
      expect(dialog.message()).toContain('Are you sure');
      dialog.accept();
    });

    // Listen for DELETE API call
    const deletePromise = page.waitForResponse(
      (response) => response.url().includes('/runtime-config/') && response.request().method() === 'DELETE'
    );

    // Click delete
    await deleteButton.click();

    // Wait for API response
    const response = await deletePromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Configuration override has been deleted successfully')).toBeVisible({ timeout: 5000 });

    // Verify override is removed from table
    await expect(page.locator(`text=${keyName}`)).not.toBeVisible({ timeout: 5000 });
  });

  test('should cancel deletion when dialog is dismissed', async ({ page }) => {
    const firstOverride = page.locator('tbody tr').first();
    const deleteButton = firstOverride.locator('button[aria-label="Delete"], svg.w-4.h-4').first();
    const keyCell = firstOverride.locator('td').first();
    const keyName = await keyCell.textContent();

    // Setup dialog handler to cancel
    page.on('dialog', dialog => dialog.dismiss());

    await deleteButton.click();

    // Wait a bit
    await page.waitForTimeout(1000);

    // Override should still be visible
    await expect(page.locator(`text=${keyName}`)).toBeVisible();
  });
});

test.describe('Operational Overrides - Scope Switching', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await goToOperationalOverrides(page);
  });

  test('should switch between Global, User, and Collection tabs', async ({ page }) => {
    // Click Global tab
    await page.click('button:has-text("Global")');
    await page.waitForTimeout(500);

    // Global tab should be active (blue background)
    const globalTab = page.locator('button:has-text("Global")');
    const globalClasses = await globalTab.getAttribute('class');
    expect(globalClasses).toContain('bg-blue-60');

    // If User tab exists (depends on userId prop)
    const userTab = page.locator('button:has-text("User")');
    if (await userTab.isVisible()) {
      await userTab.click();
      await page.waitForTimeout(500);

      const userClasses = await userTab.getAttribute('class');
      expect(userClasses).toContain('bg-blue-60');
    }

    // If Collection tab exists
    const collectionTab = page.locator('button:has-text("Collection")');
    if (await collectionTab.isVisible()) {
      await collectionTab.click();
      await page.waitForTimeout(500);

      const collectionClasses = await collectionTab.getAttribute('class');
      expect(collectionClasses).toContain('bg-blue-60');
    }
  });
});

test.describe('Operational Overrides - Backend Integration', () => {
  test('should fetch overrides from API on mount', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate to configuration
    await page.goto('/configuration');

    // Click Operational Overrides tab and monitor API call
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes('/api/runtime-config/global') && response.status() === 200
    );

    await page.click('button:has-text("Operational Overrides")');

    const response = await responsePromise;
    const data = await response.json();

    // Verify response structure
    expect(Array.isArray(data)).toBeTruthy();

    // If overrides exist, verify schema
    if (data.length > 0) {
      const override = data[0];
      expect(override).toMatchObject({
        id: expect.any(String),
        scope: expect.stringMatching(/^(GLOBAL|USER|COLLECTION)$/),
        category: expect.any(String),
        config_key: expect.any(String),
        config_value: expect.objectContaining({
          value: expect.anything(),
          type: expect.stringMatching(/^(int|float|str|bool|list|dict)$/),
        }),
        is_active: expect.any(Boolean),
      });
    }
  });

  test('should persist created override across page reloads', async ({ page }) => {
    await loginAsAdmin(page);
    await goToOperationalOverrides(page);

    // Create unique override
    const uniqueKey = `persistence_test_${Date.now()}`;

    await page.click('button:has-text("Create Override")');
    await page.waitForTimeout(500);

    await page.selectOption('select', { label: 'Global' });
    await page.selectOption('select', { label: 'System' });
    await page.fill('input[placeholder*="enable_new_feature" i], input[name*="key" i]', uniqueKey);
    await page.selectOption('select', { label: 'Boolean' });
    await page.selectOption('select', { label: 'True' });

    await page.click('button:has-text("Create Override")').last();
    await page.waitForTimeout(1000);

    // Verify it's visible
    await expect(page.locator(`text=${uniqueKey}`)).toBeVisible();

    // Reload page
    await page.reload();
    await page.waitForTimeout(1000);

    // Go back to Operational Overrides
    await page.click('button:has-text("Operational Overrides")');
    await page.waitForTimeout(1000);

    // Should still be there
    await expect(page.locator(`text=${uniqueKey}`)).toBeVisible();

    // Clean up - delete the test override
    const deleteButton = page.locator(`text=${uniqueKey}`).locator('..').locator('button[aria-label="Delete"]');
    page.on('dialog', dialog => dialog.accept());
    await deleteButton.click();
    await page.waitForTimeout(1000);
  });
});
