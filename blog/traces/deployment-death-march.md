# The Deployment Death March: 7 PRs in 2 Days

*November 13–14, 2025. Each fix revealed the next problem.*

**PRs**: [#633](https://github.com/manavgup/rag_modulo/pull/633), [#634](https://github.com/manavgup/rag_modulo/pull/634), [#635](https://github.com/manavgup/rag_modulo/pull/635), [#636](https://github.com/manavgup/rag_modulo/pull/636), [#637](https://github.com/manavgup/rag_modulo/pull/637), [#638](https://github.com/manavgup/rag_modulo/pull/638), [#639](https://github.com/manavgup/rag_modulo/pull/639)–[#640](https://github.com/manavgup/rag_modulo/pull/640)

## Context

Deploying RAG Modulo to IBM Cloud (ROKS / Code Engine) using a GitHub Actions
workflow with Ansible playbooks and IBM Cloud CLI. The workflow had been
AI-generated — Claude wrote the initial `.github/workflows/deploy_complete_app.yml`
and the Ansible roles.

## The Cascade

### PR #633 — Missing shell scripts

The workflow referenced three shell scripts that didn't exist:
- `.github/scripts/deploy-infrastructure-codeengine.sh`
- `.github/scripts/deploy-backend-codeengine.sh`
- `.github/scripts/deploy-frontend-codeengine.sh`

Claude had written the workflow referencing scripts it planned to create in
a follow-up, but the scripts were never committed. Fix: replace with inline
IBM Cloud CLI commands.

### PR #634 — Ansible version constraints block installation

The `requirements.yml` had auto-generated version constraints that pointed
to incompatible combinations. Fix: remove version constraints to let pip
resolve compatible versions.

### PR #635 — Wrong community.kubernetes version

Removing constraints in #634 caused `community.kubernetes` to resolve to an
incompatible version. Hotfix: pin to `2.0.1` specifically.

### PR #636 — Pin ALL Ansible packages

The selective pin in #635 wasn't enough — other packages were also drifting.
Fix: pin every Ansible package to the exact versions verified locally.

### PR #637 — IBM Cloud CLI installation returns HTML

The `curl -fsSL https://clis.cloud.ibm.com/install | bash` command was returning
an HTML documentation page instead of the install script. The URL had changed
behavior.

Fix: replace `curl` installation with the official `IBM/actions-ibmcloud-cli@v1`
GitHub Action.

### PR #638 — Additional IBM Cloud CLI fixes

Further configuration adjustments for the IBM Cloud CLI action — authentication
flow, plugin installation, Code Engine project setup.

### PRs #639–#640 — Missing region mapping

IBM Container Registry uses region codes (e.g., `ca-tor` for Toronto) that
weren't in the deployment script's mapping table. The image push worked but
the region-specific registry URL was wrong.

Fix: add `ca-tor` region mapping for ICR.

## Root Causes

1. **AI-generated workflow referenced non-existent files.** The workflow YAML
   was internally consistent but referenced scripts the AI intended to write
   later. There was no CI check for "do the referenced scripts exist?"

2. **Ansible version constraints were auto-generated, not tested.** The AI
   picked version ranges that looked reasonable but hadn't been installed
   together. Ansible dependency resolution is notoriously fragile.

3. **Third-party URLs change.** The IBM Cloud CLI install URL changed from
   serving a shell script to serving an HTML page. No amount of code review
   catches a URL that stops working months later.

4. **Region mappings are undocumented edge cases.** The `ca-tor` region code
   for IBM's Toronto datacenter isn't prominently documented. An AI agent
   has no way to know it's missing from the mapping table.

## The Pattern

Each fix had a 5–10 minute feedback loop (push → wait for Actions → read logs).
The cascade structure meant you couldn't skip ahead — each problem was only
visible after the previous one was fixed. Total wall-clock time: ~8 hours
across two days for what should have been a single deployment PR.

## Lesson

Infrastructure-as-code is where AI agents are most dangerous:

- **They reference resources that don't exist** (scripts, images, config files)
- **They pick version combinations that haven't been tested together**
- **They can't account for external URL changes or regional configurations**
- **The feedback loop is slow** (push-and-pray, not local testing)

For IaC, treat every AI-generated artifact as a draft. Run it locally (or in
a staging environment) before committing. Don't trust that the references exist,
the versions are compatible, or the URLs still serve what they served when the
AI's training data was collected.
