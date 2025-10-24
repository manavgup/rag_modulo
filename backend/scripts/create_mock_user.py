#!/usr/bin/env python3
"""Create the mock user in the database.

NOTE: As of the latest version, mock users are automatically created at
application startup via SystemInitializationService.initialize_default_users().

This script is now primarily a backup utility for:
- Manual user creation in emergency situations
- Testing user creation logic independently
- Recovering from user creation failures

For normal operation, simply restart the backend and the mock user will be
automatically created when SKIP_AUTH=true.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from core.config import get_settings
from core.mock_auth import ensure_mock_user_exists
from rag_solution.file_management.database import get_db

if __name__ == "__main__":
    print("\n🔧 Creating Mock User\n")

    settings = get_settings()

    # Get database session
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # Create mock user with full initialization
        user_id = ensure_mock_user_exists(db, settings)
        print("✓ Mock user created successfully!")
        print(f"  User ID: {user_id}")
        print(f"  Email: {settings.mock_user_email}")
        print(f"  Name: {settings.mock_user_name}")
        print()

    except Exception as e:
        print(f"✗ Error creating mock user: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
