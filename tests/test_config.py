import os
import pytest
from alm_orchestrator.config import Config, ConfigError


class TestConfig:
    def test_loads_from_environment(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_USER", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_PROJECT_KEY", "TEST")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        config = Config.from_env()

        assert config.jira_url == "https://test.atlassian.net"
        assert config.jira_user == "test@example.com"
        assert config.jira_api_token == "test-token"
        assert config.jira_project_key == "TEST"
        assert config.github_token == "ghp_test"
        assert config.github_repo == "owner/repo"
        assert config.anthropic_api_key == "sk-ant-test"
        assert config.poll_interval_seconds == 30  # default

    def test_custom_poll_interval(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_USER", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_PROJECT_KEY", "TEST")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("POLL_INTERVAL_SECONDS", "10")

        config = Config.from_env()

        assert config.poll_interval_seconds == 10

    def test_raises_on_missing_required(self, monkeypatch):
        # Clear all env vars
        for key in ["JIRA_URL", "JIRA_USER", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY",
                    "GITHUB_TOKEN", "GITHUB_REPO"]:
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(ConfigError) as exc_info:
            Config.from_env()

        assert "JIRA_URL" in str(exc_info.value)

    def test_repo_owner_and_name_parsing(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_USER", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_PROJECT_KEY", "TEST")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setenv("GITHUB_REPO", "acme-corp/recipe-api")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        config = Config.from_env()

        assert config.github_owner == "acme-corp"
        assert config.github_repo_name == "recipe-api"

    def test_anthropic_api_key_is_optional(self, monkeypatch):
        monkeypatch.setenv("JIRA_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_USER", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("JIRA_PROJECT_KEY", "TEST")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        config = Config.from_env()

        assert config.anthropic_api_key is None
