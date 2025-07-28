# Changelog

## [1.1.0] - 2025-07-27
### Added
- Stage 1 and Stage 2 pipeline redesign finalized and implemented.
- Title/body structuring and venting filter in Stage 1.
- Full-batch processing and structured JSON schema enforcement in Stage 2.
- Verbose logging across both stages.
- Regenerated v1.1 PDF reports with improved clustering.

### Notes
- Media-tagging logic for Stage 1 was prototyped but not integrated.
- All Stage 2 input files currently well below token limit; fallback chunking disabled for now.
- Utility module refactor (e.g., token_utils.py) deferred for future version.