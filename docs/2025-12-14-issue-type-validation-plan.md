# Issue Type Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add issue type validation to all actions so each only runs on appropriate Jira issue types (Bug/Story).

**Architecture:** Add `allowed_issue_types` property and `validate_issue_type()` method to `BaseAction`. Each action declares its allowed types and calls validation at the start of `execute()`. Invalid types are rejected with a comment, label removal, and DEBUG log.

**Tech Stack:** Python, pytest, unittest.mock

---

## Task 1: Add validate_issue_type to BaseAction

**Files:**
- Modify: `src/alm_orchestrator/actions/base.py`
- Create: `tests/test_actions/test_base.py`

### Step 1: Write the failing test for valid issue type

Create `tests/test_actions/test_base.py`:

```python
"""Tests for BaseAction validation."""

import pytest
from unittest.mock import MagicMock
from alm_orchestrator.actions.base import BaseAction


class ConcreteAction(BaseAction):
    """Concrete implementation for testing."""

    @property
    def label(self) -> str:
        return "ai-test"

    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug"]

    def execute(self, issue, jira_client, github_client, claude_executor) -> str:
        return "executed"


class TestValidateIssueType:
    def test_valid_issue_type_returns_true(self):
        """Valid issue type returns True without posting comment."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Bug"

        mock_jira = MagicMock()

        action = ConcreteAction(prompts_dir="/tmp/prompts")
        result = action.validate_issue_type(mock_issue, mock_jira)

        assert result is True
        mock_jira.add_comment.assert_not_called()
        mock_jira.remove_label.assert_not_called()
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_base.py::TestValidateIssueType::test_valid_issue_type_returns_true -v`

Expected: FAIL with `AttributeError: 'ConcreteAction' object has no attribute 'validate_issue_type'`

### Step 3: Add allowed_issue_types property and validate_issue_type method to BaseAction

Edit `src/alm_orchestrator/actions/base.py`. Add import at top:

```python
import logging

logger = logging.getLogger(__name__)
```

Add after the `get_template_path` method (after line 63):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        """Issue types this action can run on. Override in subclasses.

        Returns:
            List of allowed issue type names (e.g., ["Bug", "Story"]).
            Empty list means no validation (all types allowed).
        """
        return []

    def validate_issue_type(self, issue, jira_client) -> bool:
        """Check if issue type is allowed. Posts rejection comment if not.

        Args:
            issue: Jira issue object.
            jira_client: JiraClient for posting comments and removing labels.

        Returns:
            True if valid (or no validation configured), False if rejected.
        """
        allowed = self.allowed_issue_types
        if not allowed:
            return True

        issue_type = issue.fields.issuetype.name
        if issue_type in allowed:
            return True

        # Log rejection
        logger.debug(
            f"Rejecting {issue.key}: {self.label} does not support issue type {issue_type}"
        )

        # Post rejection comment
        allowed_str = ", ".join(allowed)
        header = "INVALID ISSUE TYPE"
        comment = (
            f"{header}\n"
            f"{'=' * len(header)}\n\n"
            f"The {self.label} action only works on: {allowed_str}\n\n"
            f"This issue is a {issue_type}. "
            f"Please use an appropriate action for this issue type."
        )
        jira_client.add_comment(issue.key, comment)

        # Remove label
        jira_client.remove_label(issue.key, self.label)

        return False
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_base.py::TestValidateIssueType::test_valid_issue_type_returns_true -v`

Expected: PASS

### Step 5: Write test for invalid issue type

Add to `tests/test_actions/test_base.py`:

```python
    def test_invalid_issue_type_returns_false_and_posts_comment(self, caplog):
        """Invalid issue type returns False, posts comment, removes label, logs DEBUG."""
        import logging
        caplog.set_level(logging.DEBUG)

        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Story"

        mock_jira = MagicMock()

        action = ConcreteAction(prompts_dir="/tmp/prompts")
        result = action.validate_issue_type(mock_issue, mock_jira)

        assert result is False

        # Verify comment was posted
        mock_jira.add_comment.assert_called_once()
        comment_args = mock_jira.add_comment.call_args[0]
        assert comment_args[0] == "TEST-123"
        assert "INVALID ISSUE TYPE" in comment_args[1]
        assert "ai-test" in comment_args[1]
        assert "Bug" in comment_args[1]
        assert "Story" in comment_args[1]

        # Verify label was removed
        mock_jira.remove_label.assert_called_once_with("TEST-123", "ai-test")

        # Verify DEBUG log
        assert any(
            "Rejecting TEST-123" in record.message
            and "Story" in record.message
            for record in caplog.records
            if record.levelno == logging.DEBUG
        )
```

### Step 6: Run test to verify it passes

Run: `pytest tests/test_actions/test_base.py::TestValidateIssueType::test_invalid_issue_type_returns_false_and_posts_comment -v`

Expected: PASS

### Step 7: Write test for empty allowed list (no validation)

Add to `tests/test_actions/test_base.py`:

```python
class NoValidationAction(BaseAction):
    """Action with no issue type validation."""

    @property
    def label(self) -> str:
        return "ai-novalidation"

    def execute(self, issue, jira_client, github_client, claude_executor) -> str:
        return "executed"


class TestValidateIssueTypeNoValidation:
    def test_empty_allowed_list_returns_true(self):
        """Empty allowed_issue_types returns True for any issue type."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Epic"

        mock_jira = MagicMock()

        action = NoValidationAction(prompts_dir="/tmp/prompts")
        result = action.validate_issue_type(mock_issue, mock_jira)

        assert result is True
        mock_jira.add_comment.assert_not_called()
        mock_jira.remove_label.assert_not_called()
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_base.py::TestValidateIssueTypeNoValidation::test_empty_allowed_list_returns_true -v`

Expected: PASS

### Step 9: Run all base tests

Run: `pytest tests/test_actions/test_base.py -v`

Expected: All 3 tests PASS

### Step 10: Commit

```bash
git add src/alm_orchestrator/actions/base.py tests/test_actions/test_base.py
git commit -m "feat: add issue type validation to BaseAction"
```

---

## Task 2: Add validation to InvestigateAction (Bug only)

**Files:**
- Modify: `src/alm_orchestrator/actions/investigate.py:9-16` (add property after label)
- Modify: `src/alm_orchestrator/actions/investigate.py:16` (add validation at start of execute)
- Modify: `tests/test_actions/test_investigate.py`

### Step 1: Write failing test for allowed_issue_types property

Add to `tests/test_actions/test_investigate.py` in `TestInvestigateAction` class:

```python
    def test_allowed_issue_types(self):
        action = InvestigateAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_investigate.py::TestInvestigateAction::test_allowed_issue_types -v`

Expected: FAIL with `AssertionError: assert [] == ['Bug']`

### Step 3: Add allowed_issue_types property to InvestigateAction

Edit `src/alm_orchestrator/actions/investigate.py`. Add after line 14 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_investigate.py::TestInvestigateAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejecting invalid type

Add to `tests/test_actions/test_investigate.py` in `TestInvestigateAction` class:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Story"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = InvestigateAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        # Should not clone repo or invoke Claude
        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()

        # Should post rejection comment and remove label
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        mock_jira.remove_label.assert_called_once_with("TEST-123", "ai-investigate")

        # Should return rejection message
        assert "Rejected" in result
        assert "TEST-123" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_investigate.py::TestInvestigateAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL (clone_repo is called, wrong assertions)

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/investigate.py`. Add at line 28 (after getting description, before cloning):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_investigate.py::TestInvestigateAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing test to include issue type

Edit `tests/test_actions/test_investigate.py`. In `test_execute_flow`, add after line 19:

```python
        mock_issue.fields.issuetype.name = "Bug"
```

In `test_cleanup_on_error`, add after line 67:

```python
        mock_issue.fields.issuetype.name = "Bug"
```

### Step 10: Run all investigate tests

Run: `pytest tests/test_actions/test_investigate.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/investigate.py tests/test_actions/test_investigate.py
git commit -m "feat: add issue type validation to InvestigateAction (Bug only)"
```

---

## Task 3: Add validation to RecommendAction (Bug, Story)

**Files:**
- Modify: `src/alm_orchestrator/actions/recommend.py:15-19`
- Modify: `tests/test_actions/test_recommend.py`

### Step 1: Write failing test for allowed_issue_types

Add to `tests/test_actions/test_recommend.py`:

```python
    def test_allowed_issue_types(self):
        action = RecommendAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug", "Story"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_recommend.py::TestRecommendAction::test_allowed_issue_types -v`

Expected: FAIL

### Step 3: Add allowed_issue_types property

Edit `src/alm_orchestrator/actions/recommend.py`. Add after line 17 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug", "Story"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_recommend.py::TestRecommendAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejection

Add to `tests/test_actions/test_recommend.py`:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug/Story issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Epic"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = RecommendAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_recommend.py::TestRecommendAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/recommend.py`. Add after line 33 (after getting description, before fetching investigation comment):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_recommend.py::TestRecommendAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing tests to include issue type

Add `mock_issue.fields.issuetype.name = "Bug"` to all existing tests in the file that create a mock_issue.

### Step 10: Run all recommend tests

Run: `pytest tests/test_actions/test_recommend.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/recommend.py tests/test_actions/test_recommend.py
git commit -m "feat: add issue type validation to RecommendAction (Bug, Story)"
```

---

## Task 4: Add validation to ImpactAction (Bug, Story)

**Files:**
- Modify: `src/alm_orchestrator/actions/impact.py:9-16`
- Create test file: `tests/test_actions/test_impact.py`

### Step 1: Create test file with allowed_issue_types test

Create `tests/test_actions/test_impact.py`:

```python
"""Tests for impact action handler."""

import pytest
from unittest.mock import MagicMock
from alm_orchestrator.actions.impact import ImpactAction
from alm_orchestrator.claude_executor import ClaudeResult


class TestImpactAction:
    def test_label_property(self):
        action = ImpactAction(prompts_dir="/tmp/prompts")
        assert action.label == "ai-impact"

    def test_allowed_issue_types(self):
        action = ImpactAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug", "Story"]

    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug/Story issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Task"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = ImpactAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result

    def test_execute_flow(self):
        """Test successful execution for valid Bug type."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Performance degradation"
        mock_issue.fields.description = "API response times increased"
        mock_issue.fields.issuetype.name = "Bug"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_github.clone_repo.return_value = "/tmp/work-dir"

        mock_result = ClaudeResult(
            content="Impact: High - affects all API consumers",
            cost_usd=0.05,
            duration_ms=5000,
            session_id="test-session"
        )
        mock_claude = MagicMock()
        mock_claude.execute_with_template.return_value = mock_result

        action = ImpactAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_called_once()
        mock_claude.execute_with_template.assert_called_once()
        mock_jira.add_comment.assert_called_once()
        assert "IMPACT ANALYSIS" in mock_jira.add_comment.call_args[0][1]
        mock_jira.remove_label.assert_called_once_with("TEST-123", "ai-impact")
        mock_github.cleanup.assert_called_once()
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_actions/test_impact.py -v`

Expected: `test_allowed_issue_types` FAIL, `test_execute_rejects_invalid_issue_type` FAIL

### Step 3: Add allowed_issue_types property to ImpactAction

Edit `src/alm_orchestrator/actions/impact.py`. Add after line 14 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug", "Story"]
```

### Step 4: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/impact.py`. Add after line 30 (after getting description, before cloning):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 5: Run all impact tests

Run: `pytest tests/test_actions/test_impact.py -v`

Expected: All tests PASS

### Step 6: Commit

```bash
git add src/alm_orchestrator/actions/impact.py tests/test_actions/test_impact.py
git commit -m "feat: add issue type validation to ImpactAction (Bug, Story)"
```

---

## Task 5: Add validation to FixAction (Bug only)

**Files:**
- Modify: `src/alm_orchestrator/actions/fix.py:15-22`
- Modify: `tests/test_actions/test_fix.py`

### Step 1: Write failing test for allowed_issue_types

Add to `tests/test_actions/test_fix.py` in `TestFixAction` class:

```python
    def test_allowed_issue_types(self):
        action = FixAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_fix.py::TestFixAction::test_allowed_issue_types -v`

Expected: FAIL

### Step 3: Add allowed_issue_types property

Edit `src/alm_orchestrator/actions/fix.py`. Add after line 20 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_fix.py::TestFixAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejection

Add to `tests/test_actions/test_fix.py`:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Story"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = FixAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_fix.py::TestFixAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/fix.py`. Add after line 37 (after getting description, before calling `_build_prior_analysis_section`):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_fix.py::TestFixAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing tests to include issue type

Add `mock_issue.fields.issuetype.name = "Bug"` to all existing tests that create a mock_issue.

### Step 10: Run all fix tests

Run: `pytest tests/test_actions/test_fix.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/fix.py tests/test_actions/test_fix.py
git commit -m "feat: add issue type validation to FixAction (Bug only)"
```

---

## Task 6: Add validation to ImplementAction (Story only)

**Files:**
- Modify: `src/alm_orchestrator/actions/implement.py:16-23`
- Modify: `tests/test_actions/test_implement.py`

### Step 1: Write failing test for allowed_issue_types

Add to `tests/test_actions/test_implement.py`:

```python
    def test_allowed_issue_types(self):
        action = ImplementAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Story"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_implement.py::TestImplementAction::test_allowed_issue_types -v`

Expected: FAIL

### Step 3: Add allowed_issue_types property

Edit `src/alm_orchestrator/actions/implement.py`. Add after line 21 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Story"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_implement.py::TestImplementAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejection

Add to `tests/test_actions/test_implement.py`:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Story issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Bug"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = ImplementAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_implement.py::TestImplementAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/implement.py`. Add after line 37 (after getting description, before calling `_build_prior_analysis_section`):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_implement.py::TestImplementAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing tests to include issue type

Add `mock_issue.fields.issuetype.name = "Story"` to all existing tests that create a mock_issue.

### Step 10: Run all implement tests

Run: `pytest tests/test_actions/test_implement.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/implement.py tests/test_actions/test_implement.py
git commit -m "feat: add issue type validation to ImplementAction (Story only)"
```

---

## Task 7: Add validation to CodeReviewAction (Bug, Story)

**Files:**
- Modify: `src/alm_orchestrator/actions/code_review.py:11-18`
- Modify: `tests/test_actions/test_code_review.py`

### Step 1: Write failing test for allowed_issue_types

Add to `tests/test_actions/test_code_review.py`:

```python
    def test_allowed_issue_types(self):
        action = CodeReviewAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug", "Story"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_code_review.py::TestCodeReviewAction::test_allowed_issue_types -v`

Expected: FAIL

### Step 3: Add allowed_issue_types property

Edit `src/alm_orchestrator/actions/code_review.py`. Add after line 16 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug", "Story"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_code_review.py::TestCodeReviewAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejection

Add to `tests/test_actions/test_code_review.py`:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug/Story issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Task"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = CodeReviewAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_code_review.py::TestCodeReviewAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/code_review.py`. Add after line 31 (after getting description, before fetching comments):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_code_review.py::TestCodeReviewAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing tests to include issue type

Add `mock_issue.fields.issuetype.name = "Bug"` or `"Story"` to all existing tests that create a mock_issue.

### Step 10: Run all code_review tests

Run: `pytest tests/test_actions/test_code_review.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/code_review.py tests/test_actions/test_code_review.py
git commit -m "feat: add issue type validation to CodeReviewAction (Bug, Story)"
```

---

## Task 8: Add validation to SecurityReviewAction (Bug, Story)

**Files:**
- Modify: `src/alm_orchestrator/actions/security_review.py:11-18`
- Modify: `tests/test_actions/test_security_review.py`

### Step 1: Write failing test for allowed_issue_types

Add to `tests/test_actions/test_security_review.py`:

```python
    def test_allowed_issue_types(self):
        action = SecurityReviewAction(prompts_dir="/tmp/prompts")
        assert action.allowed_issue_types == ["Bug", "Story"]
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_actions/test_security_review.py::TestSecurityReviewAction::test_allowed_issue_types -v`

Expected: FAIL

### Step 3: Add allowed_issue_types property

Edit `src/alm_orchestrator/actions/security_review.py`. Add after line 16 (after `label` property):

```python
    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug", "Story"]
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_actions/test_security_review.py::TestSecurityReviewAction::test_allowed_issue_types -v`

Expected: PASS

### Step 5: Write failing test for execute rejection

Add to `tests/test_actions/test_security_review.py`:

```python
    def test_execute_rejects_invalid_issue_type(self):
        """Execute returns early for non-Bug/Story issue types."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.issuetype.name = "Epic"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_claude = MagicMock()

        action = SecurityReviewAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        mock_github.clone_repo.assert_not_called()
        mock_claude.execute_with_template.assert_not_called()
        mock_jira.add_comment.assert_called_once()
        assert "INVALID ISSUE TYPE" in mock_jira.add_comment.call_args[0][1]
        assert "Rejected" in result
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_actions/test_security_review.py::TestSecurityReviewAction::test_execute_rejects_invalid_issue_type -v`

Expected: FAIL

### Step 7: Add validation call at start of execute

Edit `src/alm_orchestrator/actions/security_review.py`. Add after line 31 (after getting description, before fetching comments):

```python
        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_actions/test_security_review.py::TestSecurityReviewAction::test_execute_rejects_invalid_issue_type -v`

Expected: PASS

### Step 9: Update existing tests to include issue type

Add `mock_issue.fields.issuetype.name = "Bug"` or `"Story"` to all existing tests that create a mock_issue.

### Step 10: Run all security_review tests

Run: `pytest tests/test_actions/test_security_review.py -v`

Expected: All tests PASS

### Step 11: Commit

```bash
git add src/alm_orchestrator/actions/security_review.py tests/test_actions/test_security_review.py
git commit -m "feat: add issue type validation to SecurityReviewAction (Bug, Story)"
```

---

## Task 9: Final Verification

### Step 1: Run all tests

Run: `pytest tests/ -v`

Expected: All tests PASS

### Step 2: Verify no regressions

Run: `pytest tests/test_actions/ -v`

Expected: All action tests PASS

### Step 3: Commit any remaining changes

```bash
git status
# If any uncommitted changes, add and commit
```
