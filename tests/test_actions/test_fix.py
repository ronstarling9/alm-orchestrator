"""Tests for fix action handler."""

import pytest
from unittest.mock import MagicMock
from alm_orchestrator.actions.fix import FixAction
from alm_orchestrator.claude_executor import ClaudeResult


class TestFixAction:
    def test_label_property(self):
        action = FixAction(prompts_dir="/tmp/prompts")
        assert action.label == "ai-fix"

    def test_execute_creates_pr(self, mocker):
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Fix orphaned recipes"
        mock_issue.fields.description = "Delete cascades incorrectly"

        mock_jira = MagicMock()

        mock_pr = MagicMock()
        mock_pr.number = 42
        mock_pr.html_url = "https://github.com/owner/repo/pull/42"

        mock_github = MagicMock()
        mock_github.clone_repo.return_value = "/tmp/work-dir"
        mock_github.create_pull_request.return_value = mock_pr

        mock_result = ClaudeResult(
            content="Fixed the cascade delete",
            cost_usd=0.10,
            duration_ms=10000,
            session_id="test-session"
        )
        mock_claude = MagicMock()
        mock_claude.execute_with_template.return_value = mock_result

        action = FixAction(prompts_dir="/tmp/prompts")
        result = action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        # Verify branch was created
        mock_github.create_branch.assert_called_once()
        branch_name = mock_github.create_branch.call_args[0][1]
        assert "test-123" in branch_name.lower()

        # Verify changes were committed and pushed
        mock_github.commit_and_push.assert_called_once()

        # Verify PR was created
        mock_github.create_pull_request.assert_called_once()
        pr_kwargs = mock_github.create_pull_request.call_args[1]
        assert "TEST-123" in pr_kwargs["title"] or "TEST-123" in pr_kwargs["body"]

        # Verify Jira comment with PR link
        mock_jira.add_comment.assert_called()
        comment_body = mock_jira.add_comment.call_args[0][1]
        assert "pull/42" in comment_body or mock_pr.html_url in comment_body

        # Verify label removed
        mock_jira.remove_label.assert_called_with("TEST-123", "ai-fix")

        # Verify cleanup
        mock_github.cleanup.assert_called_once_with("/tmp/work-dir")

    def test_cleanup_on_error(self, mocker):
        """Verify cleanup happens even when Claude fails."""
        mock_issue = MagicMock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Bug"
        mock_issue.fields.description = "Description"

        mock_jira = MagicMock()
        mock_github = MagicMock()
        mock_github.clone_repo.return_value = "/tmp/work-dir"

        mock_claude = MagicMock()
        mock_claude.execute_with_template.side_effect = Exception("Claude failed")

        action = FixAction(prompts_dir="/tmp/prompts")

        with pytest.raises(Exception, match="Claude failed"):
            action.execute(mock_issue, mock_jira, mock_github, mock_claude)

        # Cleanup should still happen
        mock_github.cleanup.assert_called_once_with("/tmp/work-dir")
