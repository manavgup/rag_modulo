# Package mapping + import normalization (pre-501/502)

Summary

- Introduce Poetry package mapping so Python can import packages from backend/ without PYTHONPATH.
- Normalize imports in tests (and any remaining code) to a single canonical root: rag_solution.*, core.*, auth.*, vectordbs.*.
- Remove PYTHONPATH=backend from Makefile/CI test steps after verification.
- Exclude Playwright tests from the unit-test job (or install playwright there) to avoid unrelated failures.

Motivation / Problem

- PR 501 moved pyproject.toml to the repo root. Some code/tests import via rag_solution.*(when backend is on sys.path) while others import via backend.rag_solution.*. Python treats these as different modules, leading to dual module registration.
- Dual registration causes SQLAlchemy to see the same mapped tables/classes twice, resulting in:
  - Table redefinition errors: "Table 'collections' is already defined for this MetaData instance"
  - Mapper conflicts: "Multiple classes found for path 'Collection'"
- CI also attempts to collect Playwright tests without playwright installed, producing unrelated unit-job failures.

Proposed Changes (No src/ layout required)

1) pyproject.toml (Poetry packages mapping)
   - Add a packages stanza so Poetry installs packages directly from backend/ into the venv import path (editable installs):

   ```toml
   [tool.poetry]
   # existing keys...
   packages = [
     { include = "rag_solution", from = "backend" },
     { include = "core",        from = "backend" },
     { include = "auth",        from = "backend" },
     { include = "vectordbs",   from = "backend" }
   ]
   ```

   - This mirrors the approach used by non-src projects like IBM/mcp-context-forge, where top-level packages are declared explicitly so imports work without PYTHONPATH.

2) Normalize imports to canonical roots
   - Replace all imports in tests (and any remaining application code) from:
     - backend.rag_solution.*→ rag_solution.*
     - backend.core.*→ core.*
     - backend.vectordbs.*→ vectordbs.*
   - This ensures each module is imported exactly once, eliminating dual registration.

   Files (representative; full list obtained via grep):
   - tests/unit/services/test_search_service.py
   - tests/unit/services/test_user_provider_service.py
   - tests/unit/services/test_user_collection_service.py
   - tests/unit/services/test_user_collection_interaction_service.py
   - tests/unit/services/test_token_warning_repository.py
   - tests/unit/services/test_token_tracking_service.py
   - tests/unit/services/test_system_initialization_service.py
   - tests/unit/services/test_prompt_template_service.py
   - tests/unit/services/test_podcast_service.py
   - tests/unit/services/test_podcast_service_unit.py
   - tests/unit/services/test_conversation_session_repository.py
   - tests/unit/services/test_conversation_message_repository.py
   - tests/unit/services/test_collection_service.py
   - tests/integration/test_search_service_integration.py
   - tests/integration/test_pipeline_service.py
   - tests/e2e/* as applicable

3) Makefile/CI
   - After confirming poetry install resolves imports, remove PYTHONPATH=backend from unit test targets.
   - In unit test job, either:
     - exclude tests/playwright from collection; or
     - install playwright as a test dependency in that job.

Out of Scope / Will Not Change

- No changes to model files (e.g., backend/rag_solution/models/collection.py, question.py, token_warning.py). We avoid using extend_existing and fix the root cause instead.

Acceptance Criteria

- All imports use rag_solution.*, core.*, auth.*, vectordbs.* (no backend.rag_solution.*).
- poetry install places backend packages on import path; unit tests run without PYTHONPATH.
- SQLAlchemy duplicate table/mapper errors are eliminated.
- Unit job does not fail on Playwright collection (excluded or properly installed).
- Unit tests pass or are reduced to only genuine functional failures unrelated to dual imports.

References

- PR 501 (Poetry move to root) and PR 502 (dependent failures)
- CI job showing failures: GitHub Actions run for PR 502
- Non-src layout reference using package mapping: IBM/mcp-context-forge (`[tool.poetry].packages`) (`https://github.com/IBM/mcp-context-forge`)

Implementation Notes

- This change is infrastructure-only and low-risk; it removes path shims, standardizes imports, and prevents dual module loading in Python.
- Once merged, 501 and 502 can be rebased on main to proceed with feature/test fixes on a clean baseline.
