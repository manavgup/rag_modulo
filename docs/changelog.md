# Changelog

All notable changes to RAG Modulo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Pages documentation deployment
- Comprehensive testing suite (947+ tests)
- Chain of Thought (CoT) reasoning with production hardening
- Unified ConversationRepository pattern
- Frontend UI component library (8 reusable components)

### Changed
- Poetry configuration moved to project root
- CI/CD pipeline optimized for faster PR feedback (~2-3 min)
- Docker images published to GHCR

### Fixed
- CoT reasoning leakage prevention (5-layer parsing strategy)
- Test isolation and async configuration
- Secret scanning with multi-layer approach

## Recent Merges

For detailed changes, see the [commit history](https://github.com/manavgup/rag_modulo/commits/main).

### Notable PRs
- #592: Phase 7 Cleanup - Remove deprecated conversation files
- #591: Phase 6 Frontend Migration
- #590: Comprehensive testing suite for ConversationRepository
- #589: Phase 4 Router Unification

## Version History

This section will be updated with formal releases once the project reaches stable versioning.

## See Also

- [Roadmap](roadmap.md) - Future plans
- [Contributing](contributing.md) - How to contribute
