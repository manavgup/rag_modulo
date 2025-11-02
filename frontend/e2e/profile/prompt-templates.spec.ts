/**
 * E2E tests for Prompt Templates in User Profile.
 *
 * Tests the complete CRUD flow for prompt templates:
 * - Viewing existing templates (Default RAG Template, Question Generation)
 * - Creating new templates
 * - Updating templates
 * - Setting default template
 * - Deleting templates
 *
 * API Endpoints tested:
 * - GET /api/users/{user_id}/prompt-templates
 * - POST /api/users/{user_id}/prompt-templates
 * - PUT /api/users/{user_id}/prompt-templates/{template_id}
 * - PUT /api/users/{user_id}/prompt-templates/{template_id}/default
 * - DELETE /api/users/{user_id}/prompt-templates/{template_id}
 */

import { test, expect, Page } from '@playwright/test';
import { login } from '../helpers/test-helpers';

// Helper function to navigate to AI Preferences
async function goToAIPreferences(page: Page) {
  await page.goto('/profile');

  // Click "AI Preferences" tab
  await page.click('button:has-text("AI Preferences")');

  // Wait for content to load
  await expect(page.locator('text=Prompt Templates').first()).toBeVisible({ timeout: 10000 });
}

test.describe('Prompt Templates - View and List', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
  });

  test('should display "Prompt Templates" section', async ({ page }) => {
    // Verify section header
    await expect(page.locator('h2:has-text("Prompt Templates"), h3:has-text("Prompt Templates")')).toBeVisible();

    // Should have "Manage Templates" button
    await expect(page.locator('button:has-text("Manage Templates")')).toBeVisible();
  });

  test('should display Default RAG Template', async ({ page }) => {
    // Look for Default RAG Template card/row
    const ragTemplate = page.locator('text=Default RAG Template').first();
    await expect(ragTemplate).toBeVisible();

    // Check for template type/description
    await expect(page.locator('text=Rag Query, text=RAG_QUERY').first()).toBeVisible();

    // Should have "Default" badge
    await expect(page.locator('text=Default').first()).toBeVisible();
  });

  test('should display Question Generation Template', async ({ page }) => {
    // Look for Question Generation Template
    const questionTemplate = page.locator('text=Question Generation Template').first();
    await expect(questionTemplate).toBeVisible();

    // Check for template type/description
    await expect(page.locator('text=Question Generation, text=QUESTION_GENERATION').first()).toBeVisible();
  });

  test('should fetch templates from API on page load', async ({ page }) => {
    // Listen for API call
    const apiPromise = page.waitForResponse(
      (response) => response.url().includes('/prompt-templates') && response.status() === 200
    );

    // Reload page to trigger API call
    await page.reload();

    // Wait for API response
    const response = await apiPromise;
    const data = await response.json();

    // Verify response structure
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThanOrEqual(2); // At least Default RAG and Question Generation

    // Verify template structure
    const template = data[0];
    expect(template).toHaveProperty('id');
    expect(template).toHaveProperty('name');
    expect(template).toHaveProperty('template_type');
    expect(template).toHaveProperty('template_format');
    expect(template).toHaveProperty('is_default');
  });
});

test.describe('Prompt Templates - Manage Templates Modal/Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
  });

  test('should open "Manage Templates" dialog/page', async ({ page }) => {
    // Click "Manage Templates" button
    await page.click('button:has-text("Manage Templates")');

    // Wait for modal/page to open
    // Could be a modal or a new page depending on implementation
    const modalOrPage = page.locator('text=Manage Prompt Templates, h1:has-text("Prompt Templates")').first();
    await expect(modalOrPage).toBeVisible({ timeout: 5000 });

    // Should have "Create New Template" button
    await expect(page.locator('button:has-text("Create"), button:has-text("New Template")')).toBeVisible();
  });

  test('should display all templates in manage view', async ({ page }) => {
    await page.click('button:has-text("Manage Templates")');

    // Wait for templates to load
    await page.waitForTimeout(1000);

    // Should see both templates
    await expect(page.locator('text=Default RAG Template')).toBeVisible();
    await expect(page.locator('text=Question Generation Template')).toBeVisible();

    // Each template should have action buttons
    const editButtons = page.locator('button[aria-label="Edit"], button:has-text("Edit")');
    expect(await editButtons.count()).toBeGreaterThanOrEqual(2);
  });
});

test.describe('Prompt Templates - Create New Template', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
    await page.click('button:has-text("Manage Templates")');
  });

  test('should open create template form', async ({ page }) => {
    // Click "Create New Template" button
    await page.click('button:has-text("Create"), button:has-text("New Template")');

    // Wait for form to appear
    await expect(page.locator('input[name="name"], input[placeholder*="name" i]')).toBeVisible({ timeout: 5000 });

    // Verify form fields
    await expect(page.locator('select[name="template_type"], select[name="type"]')).toBeVisible();
    await expect(page.locator('textarea[name="template_format"], textarea[placeholder*="template" i]')).toBeVisible();
  });

  test('should create a new custom template', async ({ page }) => {
    // Open create form
    await page.click('button:has-text("Create"), button:has-text("New Template")');
    await page.waitForTimeout(500);

    // Fill form
    await page.fill('input[name="name"], input[placeholder*="name" i]', 'My Custom Template');
    await page.selectOption('select[name="template_type"], select[name="type"]', 'CUSTOM');
    await page.fill(
      'textarea[name="template_format"], textarea[placeholder*="template" i]',
      'Answer the following question: {question}\n\nContext: {context}'
    );
    await page.fill('textarea[name="system_prompt"]', 'You are a helpful AI assistant.');

    // Add input variables (might be JSON or separate fields)
    // This depends on your UI implementation

    // Listen for API call
    const createPromise = page.waitForResponse(
      (response) => response.url().includes('/prompt-templates') && response.request().method() === 'POST'
    );

    // Submit form
    await page.click('button[type="submit"], button:has-text("Create Template")');

    // Wait for API response
    const response = await createPromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Template created successfully, text=Created').first()).toBeVisible({ timeout: 5000 });

    // Verify new template appears in list
    await expect(page.locator('text=My Custom Template')).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    // Open create form
    await page.click('button:has-text("Create"), button:has-text("New Template")');
    await page.waitForTimeout(500);

    // Try to submit without filling fields
    await page.click('button[type="submit"], button:has-text("Create Template")');

    // Should show validation errors
    await expect(
      page.locator('text=required, text=cannot be empty, text=must be filled').first()
    ).toBeVisible({ timeout: 3000 });
  });
});

test.describe('Prompt Templates - Update Template', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
    await page.click('button:has-text("Manage Templates")');
  });

  test('should open edit form for existing template', async ({ page }) => {
    // Find and click edit button for first template
    const editButton = page.locator('button[aria-label="Edit"], button:has-text("Edit")').first();
    await editButton.click();

    // Wait for form to populate
    await page.waitForTimeout(500);

    // Form should be pre-filled
    const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]');
    const nameValue = await nameInput.inputValue();
    expect(nameValue.length).toBeGreaterThan(0);
  });

  test('should update template name and description', async ({ page }) => {
    // Edit first template
    await page.locator('button[aria-label="Edit"], button:has-text("Edit")').first().click();
    await page.waitForTimeout(500);

    // Update name
    const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]');
    await nameInput.clear();
    await nameInput.fill('Updated RAG Template');

    // Listen for API call
    const updatePromise = page.waitForResponse(
      (response) => response.url().includes('/prompt-templates/') && response.request().method() === 'PUT'
    );

    // Submit form
    await page.click('button[type="submit"], button:has-text("Update"), button:has-text("Save")');

    // Wait for API response
    const response = await updatePromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Template updated, text=Updated successfully').first()).toBeVisible({ timeout: 5000 });

    // Verify updated name appears
    await expect(page.locator('text=Updated RAG Template')).toBeVisible();
  });
});

test.describe('Prompt Templates - Set Default Template', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
    await page.click('button:has-text("Manage Templates")');
  });

  test('should set a template as default', async ({ page }) => {
    // Find a non-default template
    const templateRow = page.locator('text=Question Generation Template').first();

    // Click "Set as Default" button (might be a toggle or button)
    const setDefaultButton = templateRow.locator('..').locator('button:has-text("Set as Default"), button[aria-label*="default" i]');

    // Listen for API call
    const defaultPromise = page.waitForResponse(
      (response) => response.url().includes('/prompt-templates/') && response.url().includes('/default')
    );

    await setDefaultButton.click();

    // Wait for API response
    const response = await defaultPromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Default template, text=set').first()).toBeVisible({ timeout: 5000 });

    // Verify "Default" badge appears
    await expect(
      templateRow.locator('..').locator('text=Default')
    ).toBeVisible();
  });
});

test.describe('Prompt Templates - Delete Template', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
  });

  test('should delete a custom template', async ({ page }) => {
    // First create a template to delete
    await page.click('button:has-text("Manage Templates")');
    await page.click('button:has-text("Create"), button:has-text("New Template")');
    await page.waitForTimeout(500);

    await page.fill('input[name="name"], input[placeholder*="name" i]', 'Template to Delete');
    await page.selectOption('select[name="template_type"], select[name="type"]', 'CUSTOM');
    await page.fill(
      'textarea[name="template_format"], textarea[placeholder*="template" i]',
      'Test template: {question}'
    );

    await page.click('button[type="submit"], button:has-text("Create Template")');
    await page.waitForTimeout(1000);

    // Now delete it
    const templateRow = page.locator('text=Template to Delete').first();
    const deleteButton = templateRow.locator('..').locator('button[aria-label="Delete"], button:has-text("Delete")');

    // Setup dialog handler for confirmation
    page.on('dialog', dialog => dialog.accept());

    // Listen for DELETE API call
    const deletePromise = page.waitForResponse(
      (response) => response.url().includes('/prompt-templates/') && response.request().method() === 'DELETE'
    );

    await deleteButton.click();

    // Wait for API response
    const response = await deletePromise;
    expect(response.status()).toBe(200);

    // Verify success notification
    await expect(page.locator('text=Template deleted, text=Deleted successfully').first()).toBeVisible({ timeout: 5000 });

    // Verify template is removed from list
    await expect(page.locator('text=Template to Delete')).not.toBeVisible({ timeout: 5000 });
  });

  test('should prevent deleting default template', async ({ page }) => {
    await page.click('button:has-text("Manage Templates")');

    // Try to delete Default RAG Template
    const defaultTemplate = page.locator('text=Default RAG Template').first();
    const deleteButton = defaultTemplate.locator('..').locator('button[aria-label="Delete"], button:has-text("Delete")');

    // Button should be disabled or show warning
    const isDisabled = await deleteButton.isDisabled().catch(() => false);

    if (!isDisabled) {
      // If button is enabled, clicking should show error
      await deleteButton.click();
      await expect(
        page.locator('text=Cannot delete default, text=default template cannot be deleted').first()
      ).toBeVisible({ timeout: 3000 });
    } else {
      expect(isDisabled).toBeTruthy();
    }
  });
});

test.describe('Prompt Templates - Backend Integration', () => {
  test('should load templates from database on mount', async ({ page }) => {
    // Clear browser cache to force fresh load
    await page.context().clearCookies();

    await login(page);

    // Navigate to profile
    await page.goto('/profile');

    // Click AI Preferences
    await page.click('button:has-text("AI Preferences"), text=AI Preferences');

    // Monitor network request
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes('/api/users/') && response.url().includes('/prompt-templates')
    );

    const response = await responsePromise;

    // Verify API call succeeded
    expect(response.status()).toBe(200);

    const data = await response.json();

    // Verify we got templates
    expect(Array.isArray(data)).toBeTruthy();
    expect(data.length).toBeGreaterThan(0);

    // Verify template schema
    const template = data[0];
    expect(template).toMatchObject({
      id: expect.any(String),
      user_id: expect.any(String),
      name: expect.any(String),
      template_type: expect.stringMatching(/^(RAG_QUERY|QUESTION_GENERATION|RESPONSE_EVALUATION|COT_REASONING|RERANKING|PODCAST_GENERATION|CUSTOM)$/),
      template_format: expect.any(String),
      is_default: expect.any(Boolean),
      created_at: expect.any(String),
      updated_at: expect.any(String),
    });
  });

  test('should persist created template across page reloads', async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);

    // Create a template
    await page.click('button:has-text("Manage Templates")');
    await page.click('button:has-text("Create"), button:has-text("New Template")');
    await page.waitForTimeout(500);

    const uniqueName = `Test Persistence ${Date.now()}`;
    await page.fill('input[name="name"], input[placeholder*="name" i]', uniqueName);
    await page.selectOption('select[name="template_type"], select[name="type"]', 'CUSTOM');
    await page.fill(
      'textarea[name="template_format"], textarea[placeholder*="template" i]',
      'Persistent template: {question}'
    );

    await page.click('button[type="submit"], button:has-text("Create Template")');
    await page.waitForTimeout(1000);

    // Verify it's visible
    await expect(page.locator(`text=${uniqueName}`)).toBeVisible();

    // Reload page
    await page.reload();
    await page.waitForTimeout(1000);

    // Go back to AI Preferences
    await page.click('button:has-text("AI Preferences"), text=AI Preferences');
    await page.click('button:has-text("Manage Templates")');
    await page.waitForTimeout(1000);

    // Should still be there
    await expect(page.locator(`text=${uniqueName}`)).toBeVisible();
  });
});
