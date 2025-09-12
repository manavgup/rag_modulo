#!/usr/bin/env python3
"""Show strangler pattern status with detailed breakdown."""

import json
import sys
from pathlib import Path


def show_status():
    """Show detailed strangler pattern status."""
    tracking_file = Path(".linting-progress.json")
    
    if not tracking_file.exists():
        print("❌ Strangler pattern not initialized. Run 'make init-strangler' first.")
        return 1
    
    with open(tracking_file, 'r') as f:
        data = json.load(f)
    
    print("🏛️ Strangler Pattern Status")
    print("=" * 50)
    
    compliant_files = data.get('compliant_files', [])
    non_compliant_files = data.get('non_compliant_files', [])
    new_files = data.get('new_files_requiring_compliance', [])
    legacy_files = data.get('legacy_files_exempt', [])
    
    print(f"✅ Compliant files ({len(compliant_files)}):")
    if compliant_files:
        for f in sorted(compliant_files):
            print(f"   ✅ {f}")
    else:
        print("   (none)")
    
    print(f"\n❌ Non-compliant files ({len(non_compliant_files)}):")
    if non_compliant_files:
        for f in sorted(non_compliant_files):
            print(f"   ❌ {f}")
    else:
        print("   (none)")
    
    print(f"\n🆕 New files requiring compliance ({len(new_files)}):")
    if new_files:
        for f in sorted(new_files):
            print(f"   🆕 {f}")
    else:
        print("   (none)")
    
    print(f"\n📦 Legacy files (exempt from linting) ({len(legacy_files)}):")
    if legacy_files:
        # Show first 10 and count
        for f in sorted(legacy_files)[:10]:
            print(f"   📦 {f}")
        if len(legacy_files) > 10:
            print(f"   ... and {len(legacy_files) - 10} more legacy files")
    else:
        print("   (none)")
    
    # Statistics
    total_tracked = len(compliant_files) + len(non_compliant_files) + len(new_files)
    total_files = total_tracked + len(legacy_files)
    
    print("\n📊 Statistics:")
    print(f"   Total files:        {total_files}")
    print(f"   Tracked files:      {total_tracked}")
    print(f"   Legacy files:       {len(legacy_files)}")
    print(f"   Compliance rate:    {(len(compliant_files) / total_tracked * 100) if total_tracked > 0 else 0:.1f}%")
    print(f"   Migration progress: {((total_tracked) / total_files * 100):.1f}%")
    
    print("\n💡 Next steps:")
    if new_files:
        print("   - New files need attention (they must pass linting)")
    if non_compliant_files:
        print("   - Fix non-compliant files and re-migrate them")
    if legacy_files:
        print(f"   - Migrate legacy files: make lint-migrate-file FILE=<path>")
        print(f"   - Start with: {legacy_files[0] if legacy_files else 'N/A'}")
    
    return 0


if __name__ == "__main__":
    sys.exit(show_status())