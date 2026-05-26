# The Codex Automation Saga: 15 PRs That All Failed

*October 10–11, 2025. Two days, 15 PRs, zero working automation.*

## What I Was Trying to Do

Automate issue-to-PR workflows using AI agents in GitHub Actions. The idea:
a GitHub issue gets labeled → an AI agent reads the issue → plans the implementation →
creates a PR with the code. Fully automated development.

## The Sequence

| PR | Title | Problem |
|---|---|---|
| [#367](https://github.com/manavgup/rag_modulo/pull/367) | Add AI-assisted dev workflow (Gemini + Claude) | Referenced non-existent Gemini GitHub Action |
| [#368](https://github.com/manavgup/rag_modulo/pull/368) | Use OpenAI Codex action instead of Gemini | Codex action couldn't access issue context |
| [#369](https://github.com/manavgup/rag_modulo/pull/369) | Add issue context to Codex planner prompt | Codex sandbox blocked `gh` CLI commands |
| [#370](https://github.com/manavgup/rag_modulo/pull/370) | Change Codex safety strategy to allow gh | `GH_TOKEN` not passed to sandbox |
| [#371](https://github.com/manavgup/rag_modulo/pull/371) | Pass GH_TOKEN to Codex sandbox | Planner worked; implementer had same token issue |
| [#373](https://github.com/manavgup/rag_modulo/pull/373) | Pass GH_TOKEN to implementer sandbox | Implementer couldn't fetch the plan from issue comments |
| [#374](https://github.com/manavgup/rag_modulo/pull/374) | Include plan in Codex prompt directly | Multi-line YAML variable broke prompt |
| [#375](https://github.com/manavgup/rag_modulo/pull/375) | Fix YAML syntax for plan embedding | `echo` couldn't handle multi-line `$PLAN` |
| [#376](https://github.com/manavgup/rag_modulo/pull/376) | Use printf for multi-line PLAN variable | Codex quality too low for real implementation |
| [#377](https://github.com/manavgup/rag_modulo/pull/377) | Replace Codex with Anthropic Claude API | Used wrong parameter names |
| [#378](https://github.com/manavgup/rag_modulo/pull/378) | Add Claude Code GitHub Workflow | Duplicate workflow, lint errors |
| [#379](https://github.com/manavgup/rag_modulo/pull/379) | Fix direct_prompt parameter name | Still wrong parameter format |
| [#380](https://github.com/manavgup/rag_modulo/pull/380) | Remove invalid 'mode: direct' parameter | Action still didn't execute properly |
| [#382](https://github.com/manavgup/rag_modulo/pull/382) | **Remove broken AI workflow files** | Gave up on full automation |
| [#383](https://github.com/manavgup/rag_modulo/pull/383) | Fix YAML lint + combine Claude workflows | Settled for review-only Claude workflow |

## What Actually Happened

**Phase 1 (PRs #367–#371): The Codex plumber.** Five PRs just to get environment
variables, tokens, and CLI access working inside the Codex sandbox. Each fix
revealed the next permission gap. The AI was writing workflow YAML that looked
correct but hadn't been tested against the actual sandbox restrictions.

**Phase 2 (PRs #373–#376): The YAML trap.** Four PRs trying to pass a multi-line
implementation plan through GitHub Actions YAML into a Codex prompt file.
Shell quoting, YAML escaping, and multi-line variable expansion all fought each other.
PR #375 fixed the YAML but broke the shell. PR #376 fixed the shell but by then
the Codex output quality was too low to matter.

**Phase 3 (PRs #377–#380): The platform hop.** Abandoned Codex for Claude Code.
Four more PRs chasing parameter names, action versions, and configuration formats.
Each one compiled and passed lint but failed at runtime in the Actions environment.

**Phase 4 (PRs #382–#383): The surrender.** Removed the full automation workflows.
Kept a simpler Claude Code review workflow that only comments on PRs, doesn't
create them.

## Why It Failed

1. **AI agents writing CI/CD YAML can't test it locally.** Each iteration required
   a push, a wait for Actions, and reading logs. The feedback loop was 5–10 minutes
   per attempt.

2. **Sandbox permissions are invisible until you hit them.** The Codex sandbox
   blocks `gh` by default. The Claude Code Action has different parameter names
   than the documentation suggested. None of this is discoverable by reading
   the YAML.

3. **Each AI agent wrote plausible-looking configurations for the *wrong* platform.**
   PR #367 referenced a Gemini Action that didn't exist. PR #377 used Anthropic
   API parameters instead of Claude Code Action parameters. The AI was confident
   in each case.

4. **Multi-line strings in YAML + shell + GitHub Actions = combinatorial nightmare.**
   Four PRs (#373–#376) were entirely about quoting and escaping. AI agents
   are particularly bad at this because they generate "looks right" YAML without
   testing the shell expansion path.

## What I Settled For

A Claude Code review workflow (`claude.yml`) that:
- Triggers on PR creation
- Reads the diff
- Posts a code review comment
- Does NOT create branches, commits, or PRs

This works because it's **read-only** — no sandbox permission issues, no
multi-line plan passing, no implementation quality concerns.

## Lesson

Full AI automation of issue → plan → implement → PR is not ready for production
GitHub Actions workflows (as of October 2025). The gap isn't in the AI's coding
ability — it's in the CI/CD plumbing: sandbox permissions, token passing,
YAML escaping, and action parameter formats. Every layer has its own failure
mode, and AI agents can't debug them because they can't run the workflow locally.

Start with read-only AI workflows (review, lint, comment) and add write
capabilities one at a time, testing each permission boundary manually.
