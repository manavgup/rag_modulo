#!/bin/bash
# Initialize strangler pattern for linting

set -e

echo "🔧 Initializing strangler pattern for linting..."

# Create initial tracking file
TRACKING_FILE=".linting-progress.json"

if [ ! -f "$TRACKING_FILE" ]; then
    echo "Creating initial tracking file..."
    cat > "$TRACKING_FILE" << 'EOF'
{
  "compliant_files": [],
  "non_compliant_files": [],
  "new_files_requiring_compliance": [],
  "legacy_files_exempt": []
}
EOF
fi

# Find all Python files in the project (exclude virtual environments and caches)
echo "Scanning for Python files..."
PYTHON_FILES=$(find ./backend ./scripts -name "*.py" \
    -not -path "./backend/.venv/*" \
    -not -path "*/__pycache__/*" \
    -not -path "*/.mypy_cache/*" \
    -not -path "*/.pytest_cache/*" \
    | sort)

echo "Found $(echo "$PYTHON_FILES" | wc -l) Python files"

# Add all existing files to legacy exempt list (they won't be linted initially)
echo "Adding existing files to legacy exempt list..."
python3 -c "
import json
import sys

# Read current tracking file
with open('$TRACKING_FILE', 'r') as f:
    data = json.load(f)

# Get list of Python files
python_files = '''$PYTHON_FILES'''.strip().split('\n') if '''$PYTHON_FILES'''.strip() else []

# Add to legacy exempt list
data['legacy_files_exempt'] = python_files

# Write back
with open('$TRACKING_FILE', 'w') as f:
    json.dump(data, f, indent=2)

print(f'Added {len(python_files)} files to legacy exempt list')
"

echo "✅ Strangler pattern initialized!"
echo ""
echo "Next steps:"
echo "1. New Python files will be automatically tracked for linting"
echo "2. Legacy files are exempt from linting initially"
echo "3. Use 'make lint-migrate-file FILE=path/to/file.py' to migrate legacy files"
echo "4. Use 'make lint-progress' to check compliance status"
