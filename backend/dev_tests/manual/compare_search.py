#!/usr/bin/env python3
"""
Convenience wrapper for test_search_comparison.py

Usage:
    python compare_search.py <collection_id> "search query"
"""
import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / "backend" / "dev_tests" / "manual" / "test_search_comparison.py"

# Pass all arguments through
subprocess.run([sys.executable, str(script_path)] + sys.argv[1:])
