"""Configuration management for ALM Orchestrator."""

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass(frozen=True)
class Config:
    """Immutable configuration for the orchestrator."""

    jira_url: str
    jira_user: str
    jira_api_token: str
    jira_project_key: str
    github_token: str
    github_repo: str
    anthropic_api_key: str
    poll_interval_seconds: int = 30

    @property
    def github_owner(self) -> str:
        """Extract owner from 'owner/repo' format."""
        return self.github_repo.split("/")[0]

    @property
    def github_repo_name(self) -> str:
        """Extract repo name from 'owner/repo' format."""
        return self.github_repo.split("/")[1]

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ConfigError: If required environment variables are missing.
        """
        required = [
            "JIRA_URL",
            "JIRA_USER",
            "JIRA_API_TOKEN",
            "JIRA_PROJECT_KEY",
            "GITHUB_TOKEN",
            "GITHUB_REPO",
            "ANTHROPIC_API_KEY",
        ]

        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        poll_interval = os.getenv("POLL_INTERVAL_SECONDS", "30")
        try:
            poll_interval_int = int(poll_interval)
        except ValueError:
            raise ConfigError(f"POLL_INTERVAL_SECONDS must be an integer, got: {poll_interval}")

        return cls(
            jira_url=os.environ["JIRA_URL"],
            jira_user=os.environ["JIRA_USER"],
            jira_api_token=os.environ["JIRA_API_TOKEN"],
            jira_project_key=os.environ["JIRA_PROJECT_KEY"],
            github_token=os.environ["GITHUB_TOKEN"],
            github_repo=os.environ["GITHUB_REPO"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            poll_interval_seconds=poll_interval_int,
        )
