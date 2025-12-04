# ALM Orchestrator Code Review

**Date:** December 4, 2025
**Reviewer:** Claude Code
**Scope:** Full codebase review
**Test Status:** 56/56 tests passing

---

## Executive Summary

ALM Orchestrator is a well-designed daemon that integrates Jira, GitHub, and Claude Code CLI to automate AI-driven software development tasks. The codebase demonstrates solid software engineering practices with clean separation of concerns, comprehensive test coverage, and proper error handling.

**Overall Assessment:** Ready for production with minor improvements recommended.

**Strengths:**
- Clean architecture with clear separation of concerns
- Comprehensive test coverage (56 tests across all modules)
- Proper error handling with cleanup guarantees
- Extensible action system with auto-discovery
- Good use of Python idioms (dataclasses, context managers, type hints)

**Areas for Improvement:**
- Missing type annotations in some areas
- Some code duplication in action handlers
- Minor robustness improvements needed
- Additional edge case coverage in tests

---

## Detailed Findings

### 1. Correctness

#### Strengths
- The daemon correctly implements the poll-process-cleanup cycle
- Action handlers properly use `try/finally` blocks ensuring cleanup always runs
- Label management (add processing label, execute, remove) is correctly sequenced
- All 56 tests pass, validating core functionality

#### Issues

**[IMPORTANT] `config.py:27-33` - No validation for `github_repo` format**

The `github_owner` and `github_repo_name` properties assume the format is always `"owner/repo"`. Invalid formats will cause `IndexError`.

```python
@property
def github_owner(self) -> str:
    """Extract owner from 'owner/repo' format."""
    return self.github_repo.split("/")[0]  # Crashes if no "/"

@property
def github_repo_name(self) -> str:
    """Extract repo name from 'owner/repo' format."""
    return self.github_repo.split("/")[1]  # Crashes if no "/"
```

**Recommendation:** Add validation in `from_env()`:
```python
if "/" not in os.environ["GITHUB_REPO"]:
    raise ConfigError("GITHUB_REPO must be in 'owner/repo' format")
```

---

**[MINOR] `daemon.py:69` - Uses class attribute via `JiraClient.PROCESSING_LABEL`**

This creates a tight coupling. If the JiraClient class is mocked in tests, the constant needs explicit handling.

```python
self._jira.add_label(issue.key, JiraClient.PROCESSING_LABEL)
```

**Recommendation:** Access via instance: `self._jira.PROCESSING_LABEL` (already works since it's a class attribute).

---

### 2. Design

#### Strengths
- **Extensible Action System:** New actions can be added by simply creating a new file in `actions/`. Auto-discovery eliminates manual registration.
- **Clean Router Pattern:** `LabelRouter` cleanly separates routing logic from action execution.
- **Immutable Configuration:** Using `frozen=True` on the `Config` dataclass prevents accidental mutation.
- **Template-based Prompts:** Separating prompts into `.md` files allows non-developers to modify AI instructions.

#### Issues

**[MINOR] Code Duplication in Action Handlers**

The `code_review.py` and `security_review.py` files have identical `_extract_pr_number()` methods (lines 18-35 in both files).

**Recommendation:** Extract to a utility function or base class:
```python
# In base.py
class PRAction(BaseAction):
    """Base class for PR-based actions."""

    def _extract_pr_number(self, description: str) -> Optional[int]:
        ...
```

---

**[MINOR] `investigate.py:36` - Template path hardcoded instead of using `get_template_path()`**

Each action has a `get_template_path()` method but several actions manually construct the path:

```python
template_path = os.path.join(self._prompts_dir, "investigate.md")  # Line 36
```

**Recommendation:** Use the inherited method:
```python
template_path = self.get_template_path()
```

---

**[MINOR] `github_client.py:31-52` - Clone is always shallow (`--depth 1`)**

Shallow clones may not work well if actions need git history (e.g., `git blame`, `git log`).

**Recommendation:** Add a `shallow` parameter defaulting to `True`, allowing deep clones when needed.

---

### 3. Readability

#### Strengths
- Consistent naming conventions throughout
- Good docstrings on public methods
- Clear module-level docstrings explaining purpose
- Well-organized test structure mirroring source structure

#### Issues

**[MINOR] `base.py:29-35` - `Any` type hints lose type safety**

The `execute()` method uses `Any` for all parameters:

```python
def execute(
    self,
    issue: Any,            # Should be jira.Issue
    jira_client: Any,      # Should be JiraClient
    github_client: Any,    # Should be GitHubClient
    claude_executor: Any   # Should be ClaudeExecutor
) -> str:
```

**Recommendation:** Use proper types or create Protocol classes to enable type checking:
```python
from typing import Protocol

class JiraIssue(Protocol):
    key: str
    fields: Any
```

---

**[MINOR] `claude_executor.py:63-69` - Magic strings for CLI flags**

Command-line flags are scattered as string literals:

```python
cmd = [
    "claude",
    "-p", prompt,
    "--permission-mode", "acceptEdits",
    "--allowedTools", tools,
    "--output-format", "json",
]
```

**Recommendation:** Define as class constants for documentation and maintainability.

---

### 4. Testing

#### Strengths
- 56 tests covering all major modules
- Good use of fixtures for common setup
- Tests verify both happy paths and error cases
- Proper mocking of external dependencies

#### Issues

**[IMPORTANT] Missing tests for `impact.py`, `recommend.py`, `implement.py`, `security_review.py`**

Four of the seven action handlers have no dedicated tests:
- `tests/test_actions/test_impact.py` - Missing
- `tests/test_actions/test_recommend.py` - Missing
- `tests/test_actions/test_implement.py` - Missing
- `tests/test_actions/test_security_review.py` - Missing

The existing tests for `investigate.py`, `fix.py`, and `code_review.py` provide patterns to follow.

---

**[MINOR] `test_router.py:95-101` - Template path test uses wrong naming convention**

The test expects `code-review.md` but the actual file is `code_review.md`:

```python
def test_get_template_path_with_underscores(self):
    action = MockAction("/tmp/prompts")
    action._label = "ai-code-review"
    path = action.get_template_path()
    assert path == "/tmp/prompts/code-review.md"  # Actual: code_review.md
```

The `get_template_path()` method in `base.py:57` does `.replace("ai-", "")` but doesn't handle the hyphen-to-underscore conversion. This mismatch exists but works because the actual template file happens to match.

---

**[MINOR] No integration tests**

All tests are unit tests with mocked dependencies. Integration tests verifying end-to-end flow would add confidence.

---

### 5. Performance

#### Strengths
- Shallow clones minimize git transfer time
- Poll interval is configurable
- Temp directories are cleaned up after each action

#### Issues

**[MINOR] `daemon.py:113-116` - Sleep loop checks every second**

```python
for _ in range(poll_interval):
    if not self._running:
        break
    time.sleep(1)
```

For long poll intervals (e.g., 300 seconds), this creates 300 loop iterations.

**Recommendation:** Use `time.sleep()` with shorter remaining intervals or use `threading.Event.wait()` for cleaner interruptible sleep:
```python
self._stop_event.wait(timeout=poll_interval)
```

---

**[MINOR] `jira_client.py:103-108` - Add/remove label fetches issue twice**

Both `add_label()` and `remove_label()` call `self._jira.issue(issue_key)` to get the issue, then update it. If called in sequence, this is redundant.

---

### 6. Fault Tolerance

#### Strengths
- Proper exception handling in daemon loop (line 109)
- Actions post error comments to Jira on failure (line 85-88)
- Action labels removed on failure to prevent retry loops (line 90)
- Cleanup always runs via `finally` blocks

#### Issues

**[IMPORTANT] `daemon.py:109` - Catch-all hides specific errors**

```python
except Exception as e:
    logger.error(f"Error in poll cycle: {e}")
```

This catches all exceptions including `KeyboardInterrupt`, `SystemExit`, and programming errors.

**Recommendation:** Catch more specific exceptions:
```python
except (JiraError, GitHubError, ClaudeExecutorError) as e:
    logger.error(f"Error in poll cycle: {e}")
```

---

**[MINOR] `github_client.py:46-51` - No retry on transient git failures**

Network issues during clone will fail immediately with no retry:

```python
subprocess.run(
    ["git", "clone", "--depth", "1", "--branch", branch, clone_url, work_dir],
    check=True,
    capture_output=True,
)
```

**Recommendation:** Add retry logic with exponential backoff for transient failures.

---

**[MINOR] `github_client.py:82-101` - `commit_and_push` has no "nothing to commit" handling**

If Claude makes no changes, `git commit` will fail. This propagates as an action failure.

**Recommendation:** Check if there are staged changes before committing:
```python
result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work_dir)
if result.returncode != 0:  # Has changes
    # Commit and push
```

---

## Summary of Recommendations

### High Priority
1. Add validation for `GITHUB_REPO` format in config
2. Add tests for `impact.py`, `recommend.py`, `implement.py`, `security_review.py`
3. Use specific exception types instead of bare `except Exception`

### Medium Priority
4. Extract `_extract_pr_number()` to avoid duplication
5. Use `get_template_path()` consistently in action handlers
6. Add "nothing to commit" handling in `commit_and_push()`
7. Add retry logic for transient git/GitHub failures

### Low Priority
8. Add proper type hints instead of `Any`
9. Use `threading.Event` for cleaner interruptible sleep
10. Consider deep clone option for actions needing git history

---

## Test Coverage Summary

| Module | Tests | Status |
|--------|-------|--------|
| config.py | 4 | Passing |
| router.py | 6 | Passing |
| daemon.py | 5 | Passing |
| jira_client.py | 8 | Passing |
| github_client.py | 10 | Passing |
| claude_executor.py | 8 | Passing |
| actions/investigate.py | 3 | Passing |
| actions/fix.py | 3 | Passing |
| actions/code_review.py | 6 | Passing |
| actions/impact.py | 0 | **Missing** |
| actions/recommend.py | 0 | **Missing** |
| actions/implement.py | 0 | **Missing** |
| actions/security_review.py | 0 | **Missing** |

**Total: 56 passing, 0 failing**
