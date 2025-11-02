# RAG Modulo - End-to-End Tests

Comprehensive Playwright E2E tests for RAG Modulo frontend.

## Architecture Answer: Prompt Templates

**Q: Are prompt templates stored in the database or just buried in the service?**

**A: They ARE stored in the database!** ✅

- **Database Table**: `prompt_templates`
- **API Endpoints**: `/api/users/{user_id}/prompt-templates`
- **Model**: `backend/rag_solution/models/prompt_template.py`
- **Service**: `backend/rag_solution/services/prompt_template_service.py`
- **Repository**: `backend/rag_solution/repository/prompt_template_repository.py`

### Prompt Template Schema

```sql
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  name VARCHAR(255) NOT NULL,
  template_type VARCHAR(50) NOT NULL, -- RAG_QUERY, QUESTION_GENERATION, CUSTOM, etc.
  system_prompt TEXT,
  template_format TEXT NOT NULL, -- The actual template with {variables}
  input_variables JSONB NOT NULL, -- {"question": "str", "context": "str"}
  example_inputs JSONB,
  context_strategy JSONB,
  max_context_length INTEGER,
  stop_sequences JSONB,
  validation_schema JSONB,
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT uix_name_user UNIQUE (name, user_id)
);
```

### Template Types

- `RAG_QUERY` - Default RAG Template
- `QUESTION_GENERATION` - Question Generation Template
- `RESPONSE_EVALUATION` - Response Evaluation
- `COT_REASONING` - Chain of Thought
- `RERANKING` - Reranking prompts
- `PODCAST_GENERATION` - Podcast generation
- `CUSTOM` - User-defined templates

## Test Structure

```
e2e/
├── profile/
│   └── prompt-templates.spec.ts    # User Profile -> AI Preferences -> Prompt Templates
├── system-config/
│   └── operational-overrides.spec.ts # System Configuration -> Operational Overrides
└── helpers/
    └── test-helpers.ts              # Shared helper functions
```

## Running Tests

### Prerequisites

```bash
# Install dependencies
cd frontend
npm install

# Install Playwright browsers
npx playwright install
```

### Run All Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI (recommended for development)
npm run test:e2e:ui

# Run in headed mode (see browser)
npm run test:e2e:headed
```

### Run Specific Test Files

```bash
# Prompt templates tests only
npx playwright test e2e/profile/prompt-templates.spec.ts

# Operational overrides tests only
npx playwright test e2e/system-config/operational-overrides.spec.ts
```

### Run in Debug Mode

```bash
# Debug mode with inspector
npx playwright test --debug

# Debug specific test
npx playwright test e2e/profile/prompt-templates.spec.ts --debug
```

### Run on Specific Browser

```bash
# Chromium only
npx playwright test --project=chromium

# Firefox only
npx playwright test --project=firefox

# WebKit (Safari) only
npx playwright test --project=webkit
```

## Test Reports

```bash
# Generate HTML report
npx playwright test --reporter=html

# Show report
npx playwright show-report
```

## CI/CD Integration

Tests run automatically on:
- Pull Requests (when frontend files change)
- Push to main branch

See `.github/workflows/frontend-e2e.yml` for CI configuration.

## Test Coverage

### Prompt Templates Tests

✅ **View and List**
- Display "Prompt Templates" section
- Display Default RAG Template
- Display Question Generation Template
- Fetch templates from API on page load

✅ **Manage Templates Modal/Page**
- Open "Manage Templates" dialog/page
- Display all templates in manage view

✅ **Create New Template**
- Open create template form
- Create a new custom template
- Validate required fields

✅ **Update Template**
- Open edit form for existing template
- Update template name and description

✅ **Set Default Template**
- Set a template as default

✅ **Delete Template**
- Delete a custom template
- Prevent deleting default template

✅ **Backend Integration**
- Load templates from database on mount
- Persist created template across page reloads

### Operational Overrides Tests

✅ **View and Navigation**
- Display "Operational Overrides" tab
- Navigate to Operational Overrides section
- Display empty state when no overrides exist
- Display scope tabs (Global, User, Collection)

✅ **Create Override**
- Open create override form
- Create a global feature flag
- Create an emergency override
- Create a performance tuning override with integer value
- Validate required fields
- Cancel form and hide it

✅ **Toggle Status**
- Toggle override from active to inactive
- Show visual indication for inactive overrides

✅ **Delete Override**
- Delete override with confirmation
- Cancel deletion when dialog is dismissed

✅ **Scope Switching**
- Switch between Global, User, and Collection tabs

✅ **Backend Integration**
- Fetch overrides from API on mount
- Persist created override across page reloads

## Writing New Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { login, goToAIPreferences } from '../helpers/test-helpers';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await goToAIPreferences(page);
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await page.click('button:has-text("Something")');

    // Act
    await page.fill('input[name="field"]', 'value');
    await page.click('button[type="submit"]');

    // Assert
    await expect(page.locator('text=Success')).toBeVisible();
  });
});
```

### API Response Testing

```typescript
test('should call API endpoint', async ({ page }) => {
  // Listen for API call
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes('/api/endpoint') && response.status() === 200
  );

  // Trigger action
  await page.click('button');

  // Wait for response
  const response = await responsePromise;
  const data = await response.json();

  // Verify response
  expect(data).toMatchObject({
    id: expect.any(String),
    name: expect.any(String),
  });
});
```

### Cleanup After Tests

```typescript
test.afterEach(async ({ page }) => {
  // Delete test data
  await cleanupTestData(page, 'test_');
});
```

## Troubleshooting

### Tests Failing Locally

1. **Backend not running**: Start backend with `make local-dev-backend`
2. **Frontend not running**: Tests will start dev server automatically
3. **Stale data**: Clear browser state with `npx playwright test --headed --debug`

### Flaky Tests

- Increase timeouts for slow API calls
- Add `await page.waitForTimeout(500)` after mutations
- Use `waitForResponse()` instead of `waitForTimeout()` when possible

### CI Failures

- Check screenshots in GitHub Actions artifacts
- Review HTML report in artifacts
- Run tests in Docker locally to reproduce CI environment

## Best Practices

1. **Use helper functions** - Avoid duplicating login/navigation code
2. **Wait for API responses** - Use `waitForResponse()` to verify backend calls
3. **Test real data flow** - Verify both UI changes AND API calls
4. **Clean up test data** - Delete created records in `afterEach`
5. **Use meaningful assertions** - Check both presence AND content
6. **Handle dialogs** - Use `page.on('dialog')` for confirmations
7. **Test edge cases** - Empty states, validation errors, disabled states

## Resources

- [Playwright Docs](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging](https://playwright.dev/docs/debug)
- [Selectors](https://playwright.dev/docs/selectors)
