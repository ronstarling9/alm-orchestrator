# Recommend Investigation Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Include prior `ai-investigate` results as context when running the `ai-recommend` action.

**Architecture:** Fetch the service account's Jira account ID at startup, change `get_comments()` to return author metadata, add a method to find investigation comments by author and header pattern, and pass investigation context to the recommend prompt template.

**Tech Stack:** Python, jira-python library, pytest

---

## Task 1: Add account_id Property to JiraClient

**Files:**
- Modify: `src/alm_orchestrator/jira_client.py:108-159`
- Test: `tests/test_jira_client.py`

**Step 1: Write the failing test for account_id property**

Add to `tests/test_jira_client.py` at the end of `TestJiraClient` class:

```python
def test_account_id_fetched_at_init(self, mock_config, mocker):
    """Test that account_id is fetched at initialization."""
    mock_jira = MagicMock()
    mock_myself = MagicMock()
    mock_myself.accountId = "abc123-account-id"
    mock_jira.myself.return_value = mock_myself
    mocker.patch("alm_orchestrator.jira_client.JIRA", return_value=mock_jira)
    mocker.patch.object(OAuthTokenManager, "get_token", return_value="mock-access-token")
    mocker.patch.object(OAuthTokenManager, "get_api_url", return_value="https://api.atlassian.com/ex/jira/mock-cloud-id")

    client = JiraClient(mock_config)

    assert client.account_id == "abc123-account-id"
    mock_jira.myself.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_jira_client.py::TestJiraClient::test_account_id_fetched_at_init -v`

Expected: FAIL with `AttributeError: 'JiraClient' object has no attribute 'account_id'`

**Step 3: Write minimal implementation**

In `src/alm_orchestrator/jira_client.py`, modify `JiraClient.__init__` (around line 124):

```python
def __init__(self, config: Config):
    """Initialize Jira client with configuration.

    Args:
        config: Application configuration containing Jira credentials.
    """
    self._config = config
    self._token_manager = OAuthTokenManager(
        client_id=config.jira_client_id,
        client_secret=config.jira_client_secret,
        token_url=config.atlassian_token_url,
        resources_url=config.atlassian_resources_url,
    )
    self._jira: Optional[JIRA] = None
    self._account_id: Optional[str] = None
    self._fetch_account_id()

@property
def account_id(self) -> str:
    """The Jira account ID of this service account."""
    return self._account_id

def _fetch_account_id(self) -> None:
    """Fetch and cache the service account's Jira account ID."""
    jira = self._get_jira()
    myself = jira.myself()
    self._account_id = myself["accountId"]
    logger.debug(f"Service account ID: {self._account_id}")
```

Add import at top of file if not present:

```python
import logging

logger = logging.getLogger(__name__)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_jira_client.py::TestJiraClient::test_account_id_fetched_at_init -v`

Expected: PASS

**Step 5: Run all JiraClient tests to check for regressions**

Run: `pytest tests/test_jira_client.py -v`

Expected: All tests pass. Some tests may fail because they don't mock `myself()` - fix them by adding the mock.

**Step 6: Fix any failing tests**

Add to any failing test fixtures that create a JiraClient:

```python
mock_myself = MagicMock()
mock_myself.__getitem__ = lambda self, key: "mock-account-id" if key == "accountId" else None
mock_jira.myself.return_value = mock_myself
```

**Step 7: Commit**

```bash
git add src/alm_orchestrator/jira_client.py tests/test_jira_client.py
git commit -m "feat: fetch and log service account ID at JiraClient init"
```

---

## Task 2: Change get_comments() Return Type

**Files:**
- Modify: `src/alm_orchestrator/jira_client.py:249-265`
- Test: `tests/test_jira_client.py`

**Step 1: Update the existing test for new return type**

Modify `test_get_comments_returns_bodies_newest_first` in `tests/test_jira_client.py`:

```python
def test_get_comments_returns_dicts_newest_first(self, mock_config, mocker):
    """Test that get_comments returns comment dicts sorted newest-first."""
    mock_jira = MagicMock()
    mock_myself = MagicMock()
    mock_myself.__getitem__ = lambda self, key: "mock-account-id" if key == "accountId" else None
    mock_jira.myself.return_value = mock_myself
    mocker.patch("alm_orchestrator.jira_client.JIRA", return_value=mock_jira)
    mocker.patch.object(OAuthTokenManager, "get_token", return_value="mock-access-token")
    mocker.patch.object(OAuthTokenManager, "get_api_url", return_value="https://api.atlassian.com/ex/jira/mock-cloud-id")

    # Create mock comments with created timestamps and authors
    mock_comment_1 = MagicMock()
    mock_comment_1.body = "First comment"
    mock_comment_1.created = "2024-01-01T10:00:00.000+0000"
    mock_comment_1.author.accountId = "author-1"

    mock_comment_2 = MagicMock()
    mock_comment_2.body = "Second comment"
    mock_comment_2.created = "2024-01-02T10:00:00.000+0000"
    mock_comment_2.author.accountId = "author-2"

    mock_comment_3 = MagicMock()
    mock_comment_3.body = "Third comment"
    mock_comment_3.created = "2024-01-03T10:00:00.000+0000"
    mock_comment_3.author.accountId = "author-3"

    # Mock issue with comments in arbitrary order
    mock_issue = MagicMock()
    mock_issue.fields.comment.comments = [mock_comment_2, mock_comment_1, mock_comment_3]
    mock_jira.issue.return_value = mock_issue

    client = JiraClient(mock_config)
    result = client.get_comments("TEST-123")

    # Should be sorted newest-first and include metadata
    assert len(result) == 3
    assert result[0] == {"body": "Third comment", "author_id": "author-3", "created": "2024-01-03T10:00:00.000+0000"}
    assert result[1] == {"body": "Second comment", "author_id": "author-2", "created": "2024-01-02T10:00:00.000+0000"}
    assert result[2] == {"body": "First comment", "author_id": "author-1", "created": "2024-01-01T10:00:00.000+0000"}
    mock_jira.issue.assert_called_once_with("TEST-123", fields="comment")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_jira_client.py::TestJiraClientComments::test_get_comments_returns_dicts_newest_first -v`

Expected: FAIL with assertion error (returns strings, not dicts)

**Step 3: Update implementation**

Modify `get_comments` in `src/alm_orchestrator/jira_client.py`:

```python
def get_comments(self, issue_key: str) -> List[dict]:
    """Get comments for an issue, sorted newest-first.

    Args:
        issue_key: The issue key (e.g., "TEST-123").

    Returns:
        List of comment dicts with body, author_id, and created fields,
        ordered from newest to oldest.
    """
    issue = self._get_jira().issue(issue_key, fields="comment")
    comments = issue.fields.comment.comments
    sorted_comments = sorted(
        comments,
        key=lambda c: c.created,
        reverse=True
    )
    return [
        {
            "body": c.body,
            "author_id": c.author.accountId,
            "created": c.created,
        }
        for c in sorted_comments
    ]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_jira_client.py::TestJiraClientComments::test_get_comments_returns_dicts_newest_first -v`

Expected: PASS

**Step 5: Update empty comments test**

Modify `test_get_comments_returns_empty_list_when_no_comments`:

```python
def test_get_comments_returns_empty_list_when_no_comments(self, mock_config, mocker):
    """Test that get_comments returns empty list when issue has no comments."""
    mock_jira = MagicMock()
    mock_myself = MagicMock()
    mock_myself.__getitem__ = lambda self, key: "mock-account-id" if key == "accountId" else None
    mock_jira.myself.return_value = mock_myself
    mocker.patch("alm_orchestrator.jira_client.JIRA", return_value=mock_jira)
    mocker.patch.object(OAuthTokenManager, "get_token", return_value="mock-access-token")
    mocker.patch.object(OAuthTokenManager, "get_api_url", return_value="https://api.atlassian.com/ex/jira/mock-cloud-id")

    mock_issue = MagicMock()
    mock_issue.fields.comment.comments = []
    mock_jira.issue.return_value = mock_issue

    client = JiraClient(mock_config)
    result = client.get_comments("TEST-123")

    assert result == []
```

**Step 6: Run all comment tests**

Run: `pytest tests/test_jira_client.py::TestJiraClientComments -v`

Expected: PASS

**Step 7: Commit**

```bash
git add src/alm_orchestrator/jira_client.py tests/test_jira_client.py
git commit -m "refactor: change get_comments to return dicts with author metadata"
```

---

## Task 3: Update code_review and security_review Actions

**Files:**
- Modify: `src/alm_orchestrator/actions/code_review.py:32-36`
- Modify: `src/alm_orchestrator/actions/security_review.py:32-36`
- Test: `tests/test_actions/test_code_review.py`
- Test: `tests/test_actions/test_security_review.py`

**Step 1: Run existing tests to see failures**

Run: `pytest tests/test_actions/test_code_review.py tests/test_actions/test_security_review.py -v`

Expected: FAIL because mock returns strings but code now expects dicts

**Step 2: Update code_review.py**

In `src/alm_orchestrator/actions/code_review.py`, modify lines 32-36:

```python
# Fetch comments (sorted newest-first)
comments = jira_client.get_comments(issue_key)
comment_bodies = [c["body"] for c in comments]

# Search description first, then comments
pr_number = find_pr_in_texts(description, comment_bodies)
```

**Step 3: Update security_review.py identically**

In `src/alm_orchestrator/actions/security_review.py`, make the same change.

**Step 4: Update test mocks in test_code_review.py**

Change all occurrences of:
```python
mock_jira.get_comments.return_value = ["PR #42"]
```

To:
```python
mock_jira.get_comments.return_value = [{"body": "PR #42", "author_id": "user-1", "created": "2024-01-01T10:00:00"}]
```

And:
```python
mock_jira.get_comments.return_value = []
```

Stays the same (empty list is valid for both).

And:
```python
mock_jira_client.get_comments.return_value = ["PR #42"]
```

To:
```python
mock_jira_client.get_comments.return_value = [{"body": "PR #42", "author_id": "user-1", "created": "2024-01-01T10:00:00"}]
```

And:
```python
mock_jira_client.get_comments.return_value = ["PR #99"]
```

To:
```python
mock_jira_client.get_comments.return_value = [{"body": "PR #99", "author_id": "user-1", "created": "2024-01-01T10:00:00"}]
```

**Step 5: Update test mocks in test_security_review.py**

Make the same mock changes.

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_actions/test_code_review.py tests/test_actions/test_security_review.py -v`

Expected: PASS

**Step 7: Commit**

```bash
git add src/alm_orchestrator/actions/code_review.py src/alm_orchestrator/actions/security_review.py tests/test_actions/test_code_review.py tests/test_actions/test_security_review.py
git commit -m "refactor: update review actions to use new get_comments return type"
```

---

## Task 4: Add get_investigation_comment() Method

**Files:**
- Modify: `src/alm_orchestrator/jira_client.py`
- Test: `tests/test_jira_client.py`

**Step 1: Write failing test for finding investigation comment**

Add new test class to `tests/test_jira_client.py`:

```python
class TestJiraClientInvestigation:
    """Tests for investigation comment retrieval."""

    @pytest.fixture
    def mock_jira_setup(self, mock_config, mocker):
        """Common setup for investigation tests."""
        mock_jira = MagicMock()
        mock_myself = MagicMock()
        mock_myself.__getitem__ = lambda self, key: "bot-account-id" if key == "accountId" else None
        mock_jira.myself.return_value = mock_myself
        mocker.patch("alm_orchestrator.jira_client.JIRA", return_value=mock_jira)
        mocker.patch.object(OAuthTokenManager, "get_token", return_value="mock-access-token")
        mocker.patch.object(OAuthTokenManager, "get_api_url", return_value="https://api.atlassian.com/ex/jira/mock-cloud-id")
        return mock_jira

    def test_get_investigation_comment_finds_matching(self, mock_config, mock_jira_setup):
        """Test finding investigation comment from service account."""
        mock_jira = mock_jira_setup

        mock_comment = MagicMock()
        mock_comment.body = "INVESTIGATION RESULTS\n====================\n\nRoot cause is X."
        mock_comment.created = "2024-01-01T10:00:00.000+0000"
        mock_comment.author.accountId = "bot-account-id"

        mock_issue = MagicMock()
        mock_issue.fields.comment.comments = [mock_comment]
        mock_jira.issue.return_value = mock_issue

        client = JiraClient(mock_config)
        result = client.get_investigation_comment("TEST-123")

        assert result == "INVESTIGATION RESULTS\n====================\n\nRoot cause is X."

    def test_get_investigation_comment_returns_none_when_no_match(self, mock_config, mock_jira_setup):
        """Test returns None when no investigation comment exists."""
        mock_jira = mock_jira_setup

        mock_comment = MagicMock()
        mock_comment.body = "Some other comment"
        mock_comment.created = "2024-01-01T10:00:00.000+0000"
        mock_comment.author.accountId = "other-user"

        mock_issue = MagicMock()
        mock_issue.fields.comment.comments = [mock_comment]
        mock_jira.issue.return_value = mock_issue

        client = JiraClient(mock_config)
        result = client.get_investigation_comment("TEST-123")

        assert result is None

    def test_get_investigation_comment_ignores_other_authors(self, mock_config, mock_jira_setup):
        """Test ignores investigation comments from other users."""
        mock_jira = mock_jira_setup

        mock_comment = MagicMock()
        mock_comment.body = "INVESTIGATION RESULTS\n====================\n\nFake results."
        mock_comment.created = "2024-01-01T10:00:00.000+0000"
        mock_comment.author.accountId = "imposter-account-id"

        mock_issue = MagicMock()
        mock_issue.fields.comment.comments = [mock_comment]
        mock_jira.issue.return_value = mock_issue

        client = JiraClient(mock_config)
        result = client.get_investigation_comment("TEST-123")

        assert result is None

    def test_get_investigation_comment_returns_most_recent(self, mock_config, mock_jira_setup):
        """Test returns most recent investigation comment."""
        mock_jira = mock_jira_setup

        mock_comment_old = MagicMock()
        mock_comment_old.body = "INVESTIGATION RESULTS\n====================\n\nOld results."
        mock_comment_old.created = "2024-01-01T10:00:00.000+0000"
        mock_comment_old.author.accountId = "bot-account-id"

        mock_comment_new = MagicMock()
        mock_comment_new.body = "INVESTIGATION RESULTS\n====================\n\nNew results."
        mock_comment_new.created = "2024-01-02T10:00:00.000+0000"
        mock_comment_new.author.accountId = "bot-account-id"

        mock_issue = MagicMock()
        mock_issue.fields.comment.comments = [mock_comment_old, mock_comment_new]
        mock_jira.issue.return_value = mock_issue

        client = JiraClient(mock_config)
        result = client.get_investigation_comment("TEST-123")

        assert "New results" in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_jira_client.py::TestJiraClientInvestigation -v`

Expected: FAIL with `AttributeError: 'JiraClient' object has no attribute 'get_investigation_comment'`

**Step 3: Write implementation**

Add to `src/alm_orchestrator/jira_client.py` after `get_comments`:

```python
def get_investigation_comment(self, issue_key: str) -> Optional[str]:
    """Get the most recent investigation comment from this service account.

    Looks for comments that:
    1. Were authored by this service account
    2. Start with "INVESTIGATION RESULTS"

    Args:
        issue_key: The issue key (e.g., "TEST-123").

    Returns:
        The comment body if found, None otherwise.
    """
    comments = self.get_comments(issue_key)
    for comment in comments:
        if (
            comment["author_id"] == self._account_id
            and comment["body"].startswith("INVESTIGATION RESULTS")
        ):
            return comment["body"]
    return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_jira_client.py::TestJiraClientInvestigation -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/alm_orchestrator/jira_client.py tests/test_jira_client.py
git commit -m "feat: add get_investigation_comment method to JiraClient"
```

---

## Task 5: Update RecommendAction to Use Investigation Context

**Files:**
- Modify: `src/alm_orchestrator/actions/recommend.py`
- Create: `tests/test_actions/test_recommend.py`

**Step 1: Write failing test for recommend with investigation context**

Create `tests/test_actions/test_recommend.py`:

```python
"""Tests for recommend action handler."""

import pytest
from unittest.mock import MagicMock
from alm_orchestrator.actions.recommend import RecommendAction
from alm_orchestrator.claude_executor import ClaudeResult


class TestRecommendAction:
    def test_label_property(self):
        action = RecommendAction(prompts_dir="/tmp/prompts")
        assert action.label == "ai-recommend"

    def test_execute_includes_investigation_context(self, mocker):
        """Test that investigation context is passed to Claude."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Need approach for X"
        mock_issue.fields.description = "Description here"

        mock_jira = MagicMock()
        mock_jira.get_investigation_comment.return_value = (
            "INVESTIGATION RESULTS\n====================\n\nRoot cause is Y."
        )
        mock_jira.account_id = "bot-account-id"

        mock_github = MagicMock()
        mock_github.clone_repo.return_value = "/tmp/work-dir"

        mock_result = ClaudeResult(
            content="OPTION 1: Do X\n...",
            cost_usd=0.05,
            duration_ms=5000,
            session_id="test-session"
        )
        mock_claude = MagicMock()
        mock_claude.execute_with_template.return_value = mock_result

        action = RecommendAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        # Verify investigation context was passed
        call_kwargs = mock_claude.execute_with_template.call_args[1]
        context = call_kwargs["context"]
        assert "investigation_section" in context
        assert "Root cause is Y" in context["investigation_section"]
        assert "## Prior Investigation" in context["investigation_section"]

    def test_execute_without_investigation_context(self, mocker, caplog):
        """Test that recommend works without investigation and logs debug message."""
        import logging
        caplog.set_level(logging.DEBUG)

        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Need approach for X"
        mock_issue.fields.description = "Description here"

        mock_jira = MagicMock()
        mock_jira.get_investigation_comment.return_value = None
        mock_jira.account_id = "bot-account-id"

        mock_github = MagicMock()
        mock_github.clone_repo.return_value = "/tmp/work-dir"

        mock_result = ClaudeResult(
            content="OPTION 1: Do X\n...",
            cost_usd=0.05,
            duration_ms=5000,
            session_id="test-session"
        )
        mock_claude = MagicMock()
        mock_claude.execute_with_template.return_value = mock_result

        action = RecommendAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        # Verify empty investigation section was passed
        call_kwargs = mock_claude.execute_with_template.call_args[1]
        context = call_kwargs["context"]
        assert context["investigation_section"] == ""

        # Verify debug log was emitted
        assert any(
            "No investigation comment found" in record.message
            and "TEST-123" in record.message
            for record in caplog.records
        )
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_actions/test_recommend.py -v`

Expected: FAIL because RecommendAction doesn't call `get_investigation_comment`

**Step 3: Update implementation**

Modify `src/alm_orchestrator/actions/recommend.py`:

```python
"""Recommendation action handler."""

import logging
import os
from alm_orchestrator.actions.base import BaseAction

logger = logging.getLogger(__name__)


class RecommendAction(BaseAction):
    """Handles ai-recommend label - suggests approaches."""

    @property
    def label(self) -> str:
        return "ai-recommend"

    def execute(self, issue, jira_client, github_client, claude_executor) -> str:
        """Execute recommendation generation.

        Args:
            issue: Jira issue object.
            jira_client: JiraClient for posting results.
            github_client: GitHubClient for cloning repo.
            claude_executor: ClaudeExecutor for running analysis.

        Returns:
            Summary of the action.
        """
        issue_key = issue.key
        summary = issue.fields.summary
        description = issue.fields.description or ""

        # Check for prior investigation results
        investigation_comment = jira_client.get_investigation_comment(issue_key)
        if investigation_comment:
            investigation_section = (
                "## Prior Investigation\n\n"
                "The following investigation was already performed on this issue:\n\n"
                f"{investigation_comment}"
            )
        else:
            logger.debug(
                f"No investigation comment found for {issue_key} "
                f"from account {jira_client.account_id}"
            )
            investigation_section = ""

        work_dir = github_client.clone_repo()

        try:
            template_path = os.path.join(self._prompts_dir, "recommend.md")
            result = claude_executor.execute_with_template(
                work_dir=work_dir,
                template_path=template_path,
                context={
                    "issue_key": issue_key,
                    "issue_summary": summary,
                    "issue_description": description,
                    "investigation_section": investigation_section,
                },
                action="recommend",
            )

            header = "RECOMMENDATIONS"
            comment = f"{header}\n{'=' * len(header)}\n\n{result.content}"
            jira_client.add_comment(issue_key, comment)
            jira_client.remove_label(issue_key, self.label)

            return f"Recommendations posted for {issue_key}"

        finally:
            github_client.cleanup(work_dir)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_actions/test_recommend.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/alm_orchestrator/actions/recommend.py tests/test_actions/test_recommend.py
git commit -m "feat: include investigation context in recommend action"
```

---

## Task 6: Update Recommend Prompt Template

**Files:**
- Modify: `prompts/recommend.md`

**Step 1: Add investigation_section placeholder**

Modify `prompts/recommend.md`:

```markdown
# Recommended Approaches

## Jira Ticket
**{issue_key}**: {issue_summary}

## Description
{issue_description}

{investigation_section}

## Your Task

Propose 2-3 approaches to address this issue. Do not write code, just describe the options.

For each approach:
1. **Describe the approach** - What would be done?
2. **List pros and cons** - Trade-offs of this approach
3. **Estimate complexity** - How much work is involved?

## Output Format

IMPORTANT: Use plain text only. Do not use Markdown formatting (no #, *, -, ` characters for formatting).

OPTION 1: [Name]
Description: [What this approach does]

Pros:
* [advantage 1]
* [advantage 2]

Cons:
* [disadvantage 1]

Complexity: [Low/Medium/High]

OPTION 2: [Name]
...

RECOMMENDATION
[Which option you recommend and why]
```

**Step 2: Run all tests to verify nothing broke**

Run: `pytest tests/ -v`

Expected: All tests pass

**Step 3: Commit**

```bash
git add prompts/recommend.md
git commit -m "feat: add investigation_section placeholder to recommend template"
```

---

## Task 7: Final Verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v`

Expected: All tests pass

**Step 2: Verify no regressions**

Check that all original tests still pass and new functionality works.

---

## Summary of Changes

| File | Change |
|------|--------|
| `jira_client.py` | Add `_account_id`, `account_id` property, `_fetch_account_id()`, update `get_comments()` return type, add `get_investigation_comment()` |
| `code_review.py` | Extract bodies from comment dicts |
| `security_review.py` | Extract bodies from comment dicts |
| `recommend.py` | Fetch investigation context, build section, pass to template |
| `recommend.md` | Add `{investigation_section}` placeholder |
| `test_jira_client.py` | Update existing tests, add investigation tests |
| `test_code_review.py` | Update mocks for new return type |
| `test_security_review.py` | Update mocks for new return type |
| `test_recommend.py` | New tests for investigation context |
