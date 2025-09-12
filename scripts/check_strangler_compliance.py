#!/usr/bin/env python3
"""Pre-commit hook to check strangler pattern compliance for new/modified files."""

import json
import subprocess
import sys
from pathlib import Path


def get_staged_python_files():
    """Get list of staged Python files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM", "*.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            return [f for f in files if f.endswith('.py') and f]
        return []
    except subprocess.SubprocessError:
        return []


def check_file_compliance(file_path):
    """Check if a file passes pylint and pydocstyle."""
    pylint_success = True
    pydoc_success = True
    
    # Skip if file doesn't exist (might be deleted)
    if not Path(file_path).exists():
        return True, []
    
    errors = []
    
    # Run pylint
    try:
        result = subprocess.run(
            ["pylint", "--rcfile=.pylintrc", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            pylint_success = False
            errors.append(f"Pylint issues in {file_path}:")
            errors.append(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        errors.append(f"Pylint check failed for {file_path}: {e}")
        pylint_success = False
    
    # Run pydocstyle
    try:
        result = subprocess.run(
            ["pydocstyle", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            pydoc_success = False
            errors.append(f"Pydocstyle issues in {file_path}:")
            errors.append(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        errors.append(f"Pydocstyle check failed for {file_path}: {e}")
        pydoc_success = False
    
    return pylint_success and pydoc_success, errors


def update_tracking_file(new_files, compliant_files, non_compliant_files):
    """Update the strangler pattern tracking file."""
    tracking_file = Path(".linting-progress.json")
    
    if not tracking_file.exists():
        # Initialize if doesn't exist
        data = {
            "compliant_files": [],
            "non_compliant_files": [],
            "new_files_requiring_compliance": [],
            "legacy_files_exempt": []
        }
    else:
        with open(tracking_file, 'r') as f:
            data = json.load(f)
    
    # Update with new files
    for file_path in compliant_files:
        if file_path not in data['compliant_files']:
            data['compliant_files'].append(file_path)
        # Remove from other categories
        data['non_compliant_files'] = [f for f in data['non_compliant_files'] if f != file_path]
        data['new_files_requiring_compliance'] = [f for f in data['new_files_requiring_compliance'] if f != file_path]
        data['legacy_files_exempt'] = [f for f in data['legacy_files_exempt'] if f != file_path]
    
    for file_path in non_compliant_files:
        if file_path not in data['non_compliant_files']:
            data['non_compliant_files'].append(file_path)
        # Remove from other categories
        data['compliant_files'] = [f for f in data['compliant_files'] if f != file_path]
        data['new_files_requiring_compliance'] = [f for f in data['new_files_requiring_compliance'] if f != file_path]
        data['legacy_files_exempt'] = [f for f in data['legacy_files_exempt'] if f != file_path]
    
    # Save updated data
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    """Main function."""
    staged_files = get_staged_python_files()
    
    if not staged_files:
        return 0  # No Python files to check
    
    # Filter for files we care about (backend and scripts)
    relevant_files = []
    for f in staged_files:
        if f.startswith('backend/') or f.startswith('scripts/'):
            # Skip cache and venv directories
            if '/__pycache__/' not in f and '/.venv/' not in f:
                relevant_files.append(f)
    
    if not relevant_files:
        return 0
    
    print(f"🔍 Checking {len(relevant_files)} Python files for strangler pattern compliance...")
    
    compliant_files = []
    non_compliant_files = []
    all_errors = []
    
    for file_path in relevant_files:
        print(f"   Checking {file_path}...")
        is_compliant, errors = check_file_compliance(file_path)
        
        if is_compliant:
            compliant_files.append(file_path)
            print(f"   ✅ {file_path}")
        else:
            non_compliant_files.append(file_path)
            print(f"   ❌ {file_path}")
            all_errors.extend(errors)
    
    # Update tracking file
    update_tracking_file(relevant_files, compliant_files, non_compliant_files)
    
    if non_compliant_files:
        print(f"\n❌ {len(non_compliant_files)} files failed linting compliance:")
        for error in all_errors:
            print(error)
        print("\n💡 Fix the issues above or migrate legacy files with:")
        print("   make lint-migrate-file FILE=<path>")
        return 1
    
    print(f"✅ All {len(compliant_files)} files pass strangler pattern compliance!")
    return 0


if __name__ == "__main__":
    sys.exit(main())