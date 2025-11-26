# Testing Guide: RAG Improvements (2025-01-25)

## Quick Start

### Prerequisites

- Backend running with uvicorn (hot reload enabled)
- Frontend dev server running OR built and served
- Access to collection `35751f9a-3c27-4326-8e03-91daf208b827`

---

## Test 1: CoT Response Formatting ⭐ HIGH PRIORITY

### Steps

1. Navigate to the search interface
2. Select collection ID: `35751f9a-3c27-4326-8e03-91daf208b827`
3. Ask: **"how did IBM revenue change over the years?"**

### Expected Results

✅ Response should include:

- **Headers**: `##` for main sections, `###` for subsections
- **Lists**: Bullet points or numbered lists for data points
- **Formatting**: Bold text for emphasis, proper spacing
- **Structure**: Clear organization with summary section
- **Tables**: If applicable, properly formatted tables

### What to Look For

- Clean, readable Markdown rendering
- No HTML artifacts (no `<table>`, `<div>`, etc.)
- Proper Tailwind CSS styling applied
- Headers are larger and bold
- Lists are properly indented
- Tables (if any) are responsive

### Screenshot Comparison

Compare with the screenshots you provided - the new response should look much better formatted.

---

## Test 2: Copy-to-Clipboard Functionality ⭐ HIGH PRIORITY

### Steps

1. Get any assistant response (use the query from Test 1)
2. Look at the message metadata footer (bottom of response)
3. Find the **Copy button** (document icon)
4. Click the copy button

### Expected Results

✅ Immediate feedback:

- Icon changes from document to **checkmark** (green)
- Checkmark stays for 2 seconds
- Icon returns to document after 2 seconds

✅ Clipboard content:

- Open a text editor (VS Code, Notepad, etc.)
- Paste (Ctrl+V / Cmd+V)
- Content should match the response exactly
- **Markdown syntax preserved** (##, ###, -, **, etc.)

### Test Cases

1. **Plain text response**: Copy and verify
2. **Formatted response**: Copy and verify Markdown syntax preserved
3. **Long response**: Copy and verify complete content
4. **Multiple messages**: Copy from different messages

### Error Testing

- If browser blocks clipboard access, button should show red icon briefly

---

## Test 3: Duplicate File Handling ℹ️ INFORMATIONAL

### Steps

1. Check that backend is still running without errors
2. Verify no import errors in logs

### Expected Results

✅ No changes to functionality:

- Evaluation pipelines still work
- Data ingestion still works
- Query rewriting still works

### Note

The duplicate file was **documented** but not removed for safety.
See `backend/vectordbs/utils/DEPRECATION_NOTICE.md` for details.

---

## Regression Testing

### Basic Search Functionality

- [ ] Regular search still works
- [ ] Sources accordion still works
- [ ] Token analysis still works
- [ ] Chain of Thought accordion still works

### UI/UX

- [ ] Copy button doesn't break layout
- [ ] Markdown rendering doesn't break existing responses
- [ ] All metadata items still clickable

---

## Browser Compatibility

Test copy functionality in:

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

---

## Performance Check

- [ ] No noticeable slowdown in response rendering
- [ ] Copy button responds instantly
- [ ] Markdown rendering is smooth

---

## Known Issues to Ignore

These are pre-existing and not related to our changes:

- Type errors in `answer_synthesizer.py` (line 135) - pre-existing
- Flake8 warnings in various files - pre-existing
- Mypy errors - pre-existing

---

## Success Criteria

### Must Pass ✅

1. CoT responses render with proper Markdown formatting
2. Copy button appears and works correctly
3. No new errors in backend logs
4. No regression in existing functionality

### Nice to Have 🎯

1. Markdown formatting looks professional
2. Copy button provides clear visual feedback
3. Users can easily copy and share responses

---

## Troubleshooting

### Copy Button Not Appearing

- Check browser console for errors
- Verify `messageContent` prop is being passed
- Check that `CopyButton` component imported correctly

### Markdown Not Rendering

- Check that ReactMarkdown is receiving the content
- Verify `remarkGfm` plugin is loaded
- Check browser console for rendering errors

### Backend Errors

- Check uvicorn logs for Python errors
- Verify all imports are correct
- Check that modified files have no syntax errors

---

## Reporting Issues

If you find issues:

1. Note the specific test case
2. Capture screenshot if UI-related
3. Copy error messages from console/logs
4. Note browser and version if copy-related

---

## Next Steps After Testing

1. ✅ Mark tests as passed/failed
2. 📝 Document any issues found
3. 🚀 Deploy to staging if all tests pass
4. 📊 Gather user feedback on Markdown formatting quality
