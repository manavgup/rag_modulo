# AI-Assisted Workflow - Quick Start

## 🚀 TL;DR

1. Create issue → Add `ai-assist` label
2. Review Gemini's plan → Add `plan-approved` label
3. Wait for PR → Review Claude's feedback
4. Merge if approved ✅

## Setup (One-Time)

### 1. Add Secrets

GitHub Settings → Secrets and variables → Actions:

```bash
GEMINI_API_KEY=<your-key-from-https://aistudio.google.com/app/apikey>
CLAUDE_CODE_OAUTH_TOKEN=<already-configured>
```

### 2. Create Labels

```bash
gh label create "ai-assist" --color "4285f4" --description "Triggers AI planning"
gh label create "plan-ready" --color "22c55e" --description "Plan posted, awaiting review"
gh label create "plan-approved" --color "10b981" --description "Triggers implementation"
gh label create "ai-generated" --color "a855f7" --description "PR created by AI"
```

## Usage

### Stage 1: Planning (2-3 min)

```bash
# On GitHub issue page:
1. Click "Labels" → Select "ai-assist"
2. Wait for Gemini to post plan comment
3. Review the plan carefully
```

### Stage 2: Approve Plan (Human Decision)

```bash
# If plan looks good:
→ Add "plan-approved" label

# If plan needs changes:
→ Comment feedback
→ Remove "ai-assist" label
→ Re-add after addressing feedback
```

### Stage 3: Implementation (5-10 min)

```bash
# Automatic - no action needed
# Gemini will:
✓ Create branch fix/issue-{number}
✓ Implement changes
✓ Run tests
✓ Commit with DCO
✓ Push branch
✓ Create PR
```

### Stage 4: Review (Human Decision)

```bash
# On PR page:
1. Check CI status (must be ✅)
2. Read Claude's review
3. Review code changes
4. Merge if approved
```

## When to Use

| Scenario | AI-Assist? | Why |
|----------|-----------|-----|
| Clear bug with known fix | ✅ Yes | Perfect for AI |
| Missing test coverage | ✅ Yes | Straightforward task |
| Feature with spec | ✅ Yes | Good if well-defined |
| Vague issue | ❌ No | Needs human analysis |
| Security-critical | ❌ No | Requires expert review |
| Architecture change | ❌ No | Needs human design |

## Troubleshooting

```bash
# Planning failed?
→ Check Gemini API quota
→ Verify GEMINI_API_KEY secret
→ Add more context to issue

# Implementation failed?
→ Check workflow logs
→ Verify branch doesn't exist
→ Try manual implementation

# CI checks failing?
→ Push fixes to PR branch manually
→ Close PR and start over

# Claude review missing?
→ Wait a few minutes
→ Check CLAUDE_CODE_OAUTH_TOKEN
→ Review workflow logs
```

## Examples

### Example: Bug Fix

**Issue**: "Button click doesn't submit form"

```bash
1. Add "ai-assist" label
   → Gemini analyzes issue (2 min)
   → Posts plan

2. Review plan, add "plan-approved"
   → Gemini implements fix (5 min)
   → Creates PR

3. Review PR
   → CI passes ✅
   → Claude approves ✅
   → Merge!

Total time: ~10 minutes vs 1-2 hours manual
```

### Example: Add Tests

**Issue**: "Missing tests for AuthService"

```bash
1. Add "ai-assist" label
   → Gemini creates test plan (2 min)

2. Add "plan-approved"
   → Gemini writes comprehensive tests (8 min)
   → Creates PR with 95% coverage

3. Review
   → All tests pass ✅
   → Claude suggests edge case
   → Add test for edge case
   → Merge!

Total time: ~15 minutes vs 2-3 hours manual
```

## Cost Estimate

**Per Issue**:
- Gemini Planning: ~$0.01-0.05
- Gemini Implementation: ~$0.10-0.50
- Claude Review: Free (included)
- **Total**: ~$0.11-0.55 per issue

**Monthly** (20 issues):
- AI Costs: ~$2-11/month
- Dev Time Saved: ~30-40 hours
- **ROI**: 100-200x

## Full Documentation

See [ai-assisted-workflow.md](./ai-assisted-workflow.md) for:
- Detailed architecture
- Configuration options
- Advanced use cases
- Metrics and monitoring
- Best practices
