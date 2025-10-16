#!/usr/bin/env bash
set -euo pipefail
RALPH_DIR=.ralph
PHASES_DIR="$RALPH_DIR/phases"
COMPACT_DIR="$RALPH_DIR/compacted"
LOGS_DIR="$RALPH_DIR/logs"
mkdir -p "$PHASES_DIR" "$COMPACT_DIR" "$LOGS_DIR"
cmd_run() { cat "$1" | npx --yes @sourcegraph/amp 2>&1 | tee -a "$2"; }
feature_research() {
  local issue="${1:-Feature development for RAG Modulo}"; local f="$PHASES_DIR/feature_research.md";
  sed "s/\[FEATURE_DESCRIPTION_PLACEHOLDER\]/$issue/g" "$RALPH_DIR/prompts/research_features.md" > "$f" || cp "$RALPH_DIR/prompts/research_features.md" "$f"
  cmd_run "$f" "$LOGS_DIR/feature_research.log"
}
feature_plan() {
  local f="$PHASES_DIR/feature_plan.md"; cp "$RALPH_DIR/prompts/plan_features.md" "$f"; cmd_run "$f" "$LOGS_DIR/feature_planning.log";
}
feature_implement() {
  local f="$PHASES_DIR/feature_implement.md"; cp "$RALPH_DIR/prompts/implement_features.md" "$f"; cmd_run "$f" "$LOGS_DIR/feature_implementation.log";
}
case "${1:-}" in
  research) feature_research "${2:-}";;
  plan) feature_plan;;
  implement) feature_implement;;
  full) feature_research "${2:-}"; feature_plan; feature_implement;;
  *) echo "Usage: $0 {research|plan|implement|full} [feature_description]"; exit 1;;
esac
