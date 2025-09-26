# Ralph Workflow Directory

This directory contains all the files needed for the Ralph automated development workflow.

## Directory Structure

### Prompts (`.ralph/prompts/`)
- **research_features.md** - Feature research and analysis prompts
- **research_documentation.md** - Documentation research prompts
- **plan_features.md** - Feature implementation planning prompts
- **plan_documentation.md** - Documentation planning prompts
- **implement_features.md** - Feature implementation prompts
- **implement_documentation.md** - Documentation implementation prompts

### Logs (`.ralph/logs/`)
- **ralph.log** - Main execution log with timestamps
- **claude_output_*.log** - Individual Claude execution logs
- **lint_*.log** - Test execution logs

### Context (`.ralph/context/`)
- **current_context.md** - Current context state for Claude
- Additional context files as needed

### Progress Tracking
- **progress.md** - Human-readable progress tracking
- **current_context.md** - Combined context for Claude execution

## Usage

### Running Ralph
```bash
# Start Ralph with progress tracking
./ralph-runner.sh

# Monitor progress
./ralph-progress.sh

# View logs
tail -f .ralph/logs/ralph.log
```

### Manual Usage
```bash
# Read combined context
cat .ralph/current_context.md

# Copy into Claude Code Agent
```

## Workflow

1. **Research** - Use research prompts to analyze issues
2. **Plan** - Use planning prompts to create implementation plans
3. **Implement** - Use implementation prompts to build features
4. **Track** - Monitor progress in progress.md
5. **Log** - Check logs for execution details

## File Maintenance

- **progress.md** - Updated automatically by Ralph
- **current_context.md** - Updated automatically by Ralph
- **logs/** - Created automatically by Ralph
- **prompts/** - Manual updates as needed
EOF

echo "✅ .ralph/README.md created"
