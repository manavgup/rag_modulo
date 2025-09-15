#!/usr/bin/env python3
"""Check linting progress for strangler pattern."""

import json
import sys
from pathlib import Path


def check_progress():
    """Check linting progress and show statistics."""
    tracking_file = Path(".linting-progress.json")

    if not tracking_file.exists():
        print("❌ Strangler pattern not initialized. Run 'make init-strangler' first.")
        return 1

    with open(tracking_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    compliant_count = len(data.get('compliant_files', []))
    non_compliant_count = len(data.get('non_compliant_files', []))
    new_files_count = len(data.get('new_files_requiring_compliance', []))
    legacy_count = len(data.get('legacy_files_exempt', []))

    total_tracked = compliant_count + non_compliant_count + new_files_count
    total_files = total_tracked + legacy_count

    print("🔍 Strangler Pattern Linting Progress")
    print("=" * 40)
    print(f"✅ Compliant files:     {compliant_count:3d}")
    print(f"❌ Non-compliant files: {non_compliant_count:3d}")
    print(f"🆕 New files (tracked): {new_files_count:3d}")
    print(f"📦 Legacy files (exempt): {legacy_count:3d}")
    print("-" * 40)
    print(f"📊 Total files:         {total_files:3d}")
    print(f"🎯 Coverage:            {(compliant_count / total_tracked * 100) if total_tracked > 0 else 0:.1f}% of tracked files")
    print(f"🌟 Overall progress:    {(compliant_count / total_files * 100):.1f}% of all files")

    if new_files_count > 0:
        print("\n🆕 New files requiring compliance:")
        for file_path in data['new_files_requiring_compliance']:
            print(f"   - {file_path}")

    if non_compliant_count > 0:
        print(f"\n❌ Non-compliant files ({min(5, non_compliant_count)} of {non_compliant_count}):")
        for file_path in data['non_compliant_files'][:5]:
            print(f"   - {file_path}")
        if non_compliant_count > 5:
            print(f"   ... and {non_compliant_count - 5} more")

    print("\n💡 Migrate files with: make lint-migrate-file FILE=<path>")
    return 0


if __name__ == "__main__":
    sys.exit(check_progress())
