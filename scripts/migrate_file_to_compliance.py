#!/usr/bin/env python3
"""Migrate a file from legacy exempt to full linting compliance."""

import json
import subprocess
import sys
from pathlib import Path


def run_pylint(file_path):
    """Run pylint on a file and return success/failure."""
    try:
        result = subprocess.run(
            ["pylint", "--rcfile=.pylintrc", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Pylint timed out"
    except FileNotFoundError:
        return False, "", "Pylint not found. Install with: pip install pylint"


def run_pydocstyle(file_path):
    """Run pydocstyle on a file and return success/failure."""
    try:
        result = subprocess.run(
            ["pydocstyle", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Pydocstyle timed out"
    except FileNotFoundError:
        return False, "", "Pydocstyle not found. Install with: pip install pydocstyle"


def migrate_file(file_path):
    """Migrate a file to full linting compliance."""
    tracking_file = Path(".linting-progress.json")
    
    if not tracking_file.exists():
        print("❌ Strangler pattern not initialized. Run 'make init-strangler' first.")
        return 1
    
    # Normalize file path
    file_path = str(Path(file_path).resolve().relative_to(Path.cwd()))
    if not file_path.startswith('./'):
        file_path = './' + file_path
    
    with open(tracking_file, 'r') as f:
        data = json.load(f)
    
    # Check if file is in legacy exempt list
    if file_path not in data.get('legacy_files_exempt', []):
        print(f"❌ File {file_path} is not in legacy exempt list.")
        if file_path in data.get('compliant_files', []):
            print("✅ File is already compliant!")
        elif file_path in data.get('non_compliant_files', []):
            print("❌ File is already tracked as non-compliant.")
        else:
            print("🆕 File is new and will be automatically tracked.")
        return 1
    
    print(f"🔄 Migrating {file_path} to full linting compliance...")
    
    # Test pylint compliance
    print("🔍 Running pylint...")
    pylint_success, pylint_out, pylint_err = run_pylint(file_path)
    
    # Test pydocstyle compliance  
    print("📝 Running pydocstyle...")
    pydoc_success, pydoc_out, pydoc_err = run_pydocstyle(file_path)
    
    # Update tracking data
    data['legacy_files_exempt'].remove(file_path)
    
    if pylint_success and pydoc_success:
        data['compliant_files'].append(file_path)
        print(f"✅ {file_path} is now compliant!")
    else:
        data['non_compliant_files'].append(file_path)
        print(f"❌ {file_path} is not compliant yet.")
        
        if not pylint_success:
            print("Pylint issues:")
            print(pylint_out)
            if pylint_err:
                print("Pylint errors:")
                print(pylint_err)
        
        if not pydoc_success:
            print("Pydocstyle issues:")
            print(pydoc_out)
            if pydoc_err:
                print("Pydocstyle errors:")
                print(pydoc_err)
        
        print("\n💡 Fix these issues and run the command again to mark as compliant.")
    
    # Save updated tracking data
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return 0 if pylint_success and pydoc_success else 1


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python migrate_file_to_compliance.py <file_path>")
        return 1
    
    file_path = sys.argv[1]
    return migrate_file(file_path)


if __name__ == "__main__":
    sys.exit(main())