# ALM Orchestrator - Repository Statistics

*Generated: 2025-12-11*

## Lines of Code by Type

| Type | Files | Lines |
|------|-------|-------|
| **Python (total)** | 33 | 4,419 |
| ↳ Source code (`src/`) | 18 | 1,868 |
| ↳ Tests (`tests/`) | 15 | 2,395 |
| **Markdown (total)** | 24 | 5,951 |
| ↳ Documentation (`docs/`) | 14 | 5,263 |
| ↳ Prompt templates (`prompts/`) | 7 | 350 |
| **JSON** | 8 | 415 |

## Testing

| Metric | Value |
|--------|-------|
| Unit tests | **118** |
| Test files | 15 |
| Test lines of code | 2,395 |
| Test-to-source ratio | **1.28x** (more test code than source) |

## Architecture

| Component | Count |
|-----------|-------|
| Action modules | 8 (investigate, impact, recommend, fix, implement, code_review, security_review, base) |
| Action code | 729 lines |
| Core modules | 10 (daemon, router, config, clients, executor, utils) |

## Git History

| Metric | Value |
|--------|-------|
| Total commits | 106 |
| Author | ronstarling9 (100%) |
| Project age | 8 days (Dec 3 - Dec 11, 2025) |
| Commits per day | ~13 |

## Dependencies

- **Runtime**: jira, PyGithub, python-dotenv
- **Dev**: pytest, pytest-mock

## Interesting Observations

1. **High test coverage**: 1.28x more test code than source code, indicating thorough testing practices
2. **Documentation-heavy**: 5,951 lines of markdown (more than all Python combined)
3. **Rapid development**: 106 commits in 8 days = high velocity
4. **Clean architecture**: Action system with auto-discovery, clear separation of concerns
5. **Prompt engineering focus**: 350 lines of prompt templates driving AI behavior
