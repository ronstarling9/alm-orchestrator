"""Impact analysis action handler."""

import os
from alm_orchestrator.actions.base import BaseAction

LABEL_IMPACT = "ai-impact"


class ImpactAction(BaseAction):
    """Handles ai-impact label - performs impact analysis."""

    @property
    def label(self) -> str:
        return LABEL_IMPACT

    @property
    def allowed_issue_types(self) -> list[str]:
        return ["Bug", "Story"]

    def execute(self, issue, jira_client, github_client, claude_executor) -> str:
        """Execute impact analysis.

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

        # Validate issue type
        if not self.validate_issue_type(issue, jira_client):
            return f"Rejected {issue_key}: invalid issue type"

        work_dir = github_client.clone_repo()

        try:
            template_path = os.path.join(self._prompts_dir, "impact.md")
            result = claude_executor.execute_with_template(
                work_dir=work_dir,
                template_path=template_path,
                context={
                    "issue_key": issue_key,
                    "issue_summary": summary,
                    "issue_description": description,
                },
                action="impact",
            )

            header = "IMPACT ANALYSIS"
            comment = (
                f"{header}\n{'=' * len(header)}\n\n{result.content}"
                f"\n\n---\n_Cost: ${result.cost_usd:.4f}_"
            )
            jira_client.add_comment(issue_key, comment)
            jira_client.remove_label(issue_key, self.label)

            return f"Impact analysis complete for {issue_key}"

        finally:
            github_client.cleanup(work_dir)
