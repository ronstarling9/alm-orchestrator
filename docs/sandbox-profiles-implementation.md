# Sandbox Profiles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace CLI tool flags with OS-level sandbox profiles that restrict Claude Code to the working directory with per-action permissions.

**Architecture:** Create JSON sandbox profile files in `prompts/sandbox/`. Before each Claude invocation, copy the appropriate profile to `.claude/settings.local.json` in the cloned repo. This overrides any repo settings and enables filesystem/network isolation.

**Tech Stack:** Python 3.13, pytest, Claude Code CLI sandbox features (bubblewrap)

---

## Task 1: Create Sandbox Profile Files

**Files:**
- Create: `prompts/sandbox/investigate.json`
- Create: `prompts/sandbox/fix.json`
- Create: `prompts/sandbox/implement.json`

**Step 1: Create the sandbox directory**

```bash
mkdir -p prompts/sandbox
```

**Step 2: Create investigate.json (read-only, no network)**

Create `prompts/sandbox/investigate.json`:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Read(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git log:*)",
      "Bash(git diff:*)",
      "Bash(git show:*)",
      "Bash(git blame:*)",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(wc:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(cat:*)"
    ],
    "deny": [
      "Write(**)",
      "Edit(**)",
      "WebFetch",
      "WebSearch",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(nc:*)",
      "Bash(ssh:*)",
      "Bash(scp:*)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/.env)",
      "Read(**/.env.*)"
    ]
  }
}
```

**Step 3: Create fix.json (read-write, GitHub only)**

Create `prompts/sandbox/fix.json`:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git:*)",
      "Bash(npm test:*)",
      "Bash(npm run:*)",
      "Bash(npx:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(pip3:*)",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(wc:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(cat:*)",
      "Bash(mkdir:*)",
      "Bash(rm:*)",
      "Bash(cp:*)",
      "Bash(mv:*)"
    ],
    "deny": [
      "WebFetch",
      "WebSearch",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(nc:*)",
      "Bash(ssh:*)",
      "Bash(scp:*)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/.env)",
      "Read(**/.env.*)"
    ]
  }
}
```

**Step 4: Create implement.json (read-write, package registries allowed)**

Create `prompts/sandbox/implement.json`:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(pip3:*)",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(wc:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(cat:*)",
      "Bash(mkdir:*)",
      "Bash(rm:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "WebFetch"
    ],
    "deny": [
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(nc:*)",
      "Bash(ssh:*)",
      "Bash(scp:*)",
      "Read(.env)",
      "Read(.env.*)",
      "Read(**/.env)",
      "Read(**/.env.*)"
    ]
  }
}
```

**Step 5: Commit**

```bash
git add prompts/sandbox/
git commit -m "feat: add sandbox profile configurations for Claude Code"
```

---

## Task 2: Add Profile Installation to ClaudeExecutor

**Files:**
- Modify: `src/alm_orchestrator/claude_executor.py`
- Test: `tests/test_claude_executor.py`

**Step 1: Write the failing test for profile installation**

Add to `tests/test_claude_executor.py`:

```python
class TestSandboxProfiles:
    """Tests for sandbox profile installation."""

    def test_installs_profile_to_settings_local(self, mocker, tmp_path):
        """Verify profile is copied to .claude/settings.local.json."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_json_response("Done"),
            stderr=""
        )

        # Create a mock profile
        profiles_dir = tmp_path / "sandbox"
        profiles_dir.mkdir()
        profile_file = profiles_dir / "investigate.json"
        profile_file.write_text('{"sandbox": {"enabled": true}}')

        # Create work directory
        work_dir = tmp_path / "repo"
        work_dir.mkdir()

        executor = ClaudeExecutor(profiles_dir=str(profiles_dir))
        executor.execute(
            work_dir=str(work_dir),
            prompt="Test prompt",
            profile="investigate"
        )

        # Verify settings.local.json was created
        settings_file = work_dir / ".claude" / "settings.local.json"
        assert settings_file.exists()
        assert '"sandbox"' in settings_file.read_text()
```

**Step 2: Run test to verify it fails**

```bash
source .venv/bin/activate && pytest tests/test_claude_executor.py::TestSandboxProfiles::test_installs_profile_to_settings_local -v
```

Expected: FAIL with `TypeError` (profiles_dir not accepted)

**Step 3: Add profiles_dir parameter and profile installation**

Modify `src/alm_orchestrator/claude_executor.py`:

```python
"""Claude Code CLI executor for the ALM Orchestrator."""

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeExecutorError(Exception):
    """Raised when Claude Code execution fails."""
    pass


@dataclass
class ClaudeResult:
    """Result from a Claude Code execution."""
    content: str
    cost_usd: float
    duration_ms: int
    session_id: str


class ClaudeExecutor:
    """Executes Claude Code CLI commands in headless mode."""

    DEFAULT_TIMEOUT_SECONDS = 600  # 10 minutes

    # Tool profiles for different action types (legacy, kept for compatibility)
    TOOLS_READONLY = "Bash,Read,Glob,Grep"
    TOOLS_READWRITE = "Bash,Read,Write,Edit,Glob,Grep"

    # Profile name mapping
    PROFILE_MAP = {
        "readonly": "investigate",
        "readwrite": "fix",
    }

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        profiles_dir: Optional[str] = None
    ):
        """Initialize the executor.

        Args:
            timeout_seconds: Maximum time to wait for Claude Code to complete.
                           Defaults to 600 seconds (10 minutes).
            profiles_dir: Path to directory containing sandbox profile JSON files.
                         If None, sandbox profiles are not used.
        """
        self._timeout = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._profiles_dir = Path(profiles_dir) if profiles_dir else None

    def _install_sandbox_profile(self, work_dir: str, profile: str) -> None:
        """Install a sandbox profile to the working directory.

        Args:
            work_dir: The working directory (cloned repo).
            profile: Name of the profile (without .json extension).

        Raises:
            FileNotFoundError: If the profile doesn't exist.
        """
        if self._profiles_dir is None:
            return

        profile_src = self._profiles_dir / f"{profile}.json"
        if not profile_src.exists():
            raise FileNotFoundError(f"Sandbox profile not found: {profile_src}")

        # Create .claude directory if needed
        claude_dir = Path(work_dir) / ".claude"
        claude_dir.mkdir(exist_ok=True)

        # Copy profile to settings.local.json (higher precedence than settings.json)
        profile_dst = claude_dir / "settings.local.json"
        shutil.copy(profile_src, profile_dst)
        logger.debug(f"Installed sandbox profile '{profile}' to {profile_dst}")

    def execute(
        self,
        work_dir: str,
        prompt: str,
        allowed_tools: Optional[str] = None,
        profile: Optional[str] = None
    ) -> ClaudeResult:
        """Execute Claude Code with the given prompt in headless mode.

        Args:
            work_dir: Working directory (the cloned repo).
            prompt: The prompt to send to Claude Code.
            allowed_tools: Comma-separated list of allowed tools (legacy).
                          Ignored if profile is specified and profiles_dir is set.
            profile: Sandbox profile name (e.g., "investigate", "fix", "implement").
                    If specified and profiles_dir is set, installs the profile.

        Returns:
            ClaudeResult with content and metadata.

        Raises:
            ClaudeExecutorError: If execution fails or times out.
        """
        # Install sandbox profile if available
        if profile and self._profiles_dir:
            self._install_sandbox_profile(work_dir, profile)
            # When using sandbox profiles, don't pass --allowedTools
            # The profile handles all permissions
            cmd = [
                "claude",
                "-p", prompt,
                "--output-format", "json",
            ]
        else:
            # Legacy mode: use --allowedTools
            tools = allowed_tools or self.TOOLS_READONLY
            cmd = [
                "claude",
                "-p", prompt,
                "--permission-mode", "acceptEdits",
                "--allowedTools", tools,
                "--output-format", "json",
            ]

        logger.debug(
            f"Executing Claude Code CLI in {work_dir} "
            f"(profile={profile}, timeout={self._timeout}s)"
        )

        start_time = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise ClaudeExecutorError(
                f"Claude Code timed out after {self._timeout} seconds"
            ) from e
        finally:
            elapsed = time.monotonic() - start_time
            logger.debug(f"Claude Code CLI completed in {elapsed:.1f}s")

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise ClaudeExecutorError(f"Claude Code failed: {error_msg}")

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            return ClaudeResult(
                content=data.get("result", ""),
                cost_usd=data.get("cost_usd", 0.0),
                duration_ms=data.get("duration_ms", 0),
                session_id=data.get("session_id", ""),
            )
        except json.JSONDecodeError:
            # Fall back to raw output if JSON parsing fails
            return ClaudeResult(
                content=result.stdout,
                cost_usd=0.0,
                duration_ms=0,
                session_id="",
            )

    @staticmethod
    def _escape_format_string(value: str) -> str:
        """Escape curly braces in user input to prevent format string injection.

        Args:
            value: The string value to escape.

        Returns:
            String with { and } replaced by {{ and }}.
        """
        if not isinstance(value, str):
            return value
        return value.replace("{", "{{").replace("}", "}}")

    def execute_with_template(
        self,
        work_dir: str,
        template_path: str,
        context: dict,
        allowed_tools: Optional[str] = None,
        profile: Optional[str] = None
    ) -> ClaudeResult:
        """Execute Claude Code with a prompt template.

        Args:
            work_dir: Working directory (the cloned repo).
            template_path: Path to the prompt template file.
            context: Dictionary of variables to substitute in the template.
            allowed_tools: Comma-separated list of allowed tools (legacy).
            profile: Sandbox profile name (e.g., "investigate", "fix").

        Returns:
            ClaudeResult with content and metadata.

        Raises:
            ClaudeExecutorError: If execution fails.
            FileNotFoundError: If template doesn't exist.
        """
        with open(template_path, "r") as f:
            template = f.read()

        # Escape curly braces in context values to prevent format string injection
        # (SEC-001: user-controlled Jira content could contain {malicious} patterns)
        safe_context = {
            key: self._escape_format_string(value)
            for key, value in context.items()
        }

        prompt = template.format(**safe_context)
        return self.execute(work_dir, prompt, allowed_tools, profile)
```

**Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_claude_executor.py::TestSandboxProfiles::test_installs_profile_to_settings_local -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/alm_orchestrator/claude_executor.py tests/test_claude_executor.py
git commit -m "feat: add sandbox profile installation to ClaudeExecutor"
```

---

## Task 3: Add More Executor Tests

**Files:**
- Modify: `tests/test_claude_executor.py`

**Step 1: Write test for missing profile**

Add to `tests/test_claude_executor.py` in `TestSandboxProfiles`:

```python
    def test_raises_on_missing_profile(self, mocker, tmp_path):
        """Verify FileNotFoundError when profile doesn't exist."""
        profiles_dir = tmp_path / "sandbox"
        profiles_dir.mkdir()
        work_dir = tmp_path / "repo"
        work_dir.mkdir()

        executor = ClaudeExecutor(profiles_dir=str(profiles_dir))

        with pytest.raises(FileNotFoundError, match="nonexistent"):
            executor.execute(
                work_dir=str(work_dir),
                prompt="Test",
                profile="nonexistent"
            )
```

**Step 2: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_claude_executor.py::TestSandboxProfiles::test_raises_on_missing_profile -v
```

Expected: PASS

**Step 3: Write test for legacy mode (no profiles_dir)**

Add to `tests/test_claude_executor.py` in `TestSandboxProfiles`:

```python
    def test_legacy_mode_without_profiles_dir(self, mocker, tmp_path):
        """Verify legacy --allowedTools mode when profiles_dir is None."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_json_response("Done"),
            stderr=""
        )

        work_dir = tmp_path / "repo"
        work_dir.mkdir()

        # No profiles_dir = legacy mode
        executor = ClaudeExecutor()
        executor.execute(
            work_dir=str(work_dir),
            prompt="Test",
            allowed_tools=ClaudeExecutor.TOOLS_READONLY
        )

        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
        assert "--permission-mode" in cmd

        # No settings.local.json should be created
        settings_file = work_dir / ".claude" / "settings.local.json"
        assert not settings_file.exists()
```

**Step 4: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_claude_executor.py::TestSandboxProfiles::test_legacy_mode_without_profiles_dir -v
```

Expected: PASS

**Step 5: Write test for profile mode skipping --allowedTools**

Add to `tests/test_claude_executor.py` in `TestSandboxProfiles`:

```python
    def test_profile_mode_skips_allowed_tools_flag(self, mocker, tmp_path):
        """Verify --allowedTools is NOT passed when using sandbox profile."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_json_response("Done"),
            stderr=""
        )

        profiles_dir = tmp_path / "sandbox"
        profiles_dir.mkdir()
        (profiles_dir / "investigate.json").write_text('{"sandbox": {"enabled": true}}')

        work_dir = tmp_path / "repo"
        work_dir.mkdir()

        executor = ClaudeExecutor(profiles_dir=str(profiles_dir))
        executor.execute(
            work_dir=str(work_dir),
            prompt="Test",
            profile="investigate"
        )

        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" not in cmd
        assert "--permission-mode" not in cmd
```

**Step 6: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_claude_executor.py::TestSandboxProfiles::test_profile_mode_skips_allowed_tools_flag -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add tests/test_claude_executor.py
git commit -m "test: add sandbox profile edge case tests"
```

---

## Task 4: Update Daemon to Pass profiles_dir

**Files:**
- Modify: `src/alm_orchestrator/daemon.py`
- Test: `tests/test_daemon.py`

**Step 1: Read the current daemon.py to understand structure**

Read `src/alm_orchestrator/daemon.py` to find where `ClaudeExecutor` is instantiated.

**Step 2: Write failing test for daemon using profiles_dir**

Add to `tests/test_daemon.py`:

```python
def test_daemon_initializes_executor_with_profiles_dir(self, mocker):
    """Verify daemon passes profiles_dir to ClaudeExecutor."""
    mocker.patch.dict(os.environ, {
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_PROJECT_KEY": "TEST",
        "JIRA_CLIENT_ID": "client-id",
        "JIRA_CLIENT_SECRET": "client-secret",
        "GITHUB_TOKEN": "ghp_test",
        "GITHUB_REPO": "owner/repo",
    })

    mock_executor_class = mocker.patch("alm_orchestrator.daemon.ClaudeExecutor")

    from alm_orchestrator.daemon import Daemon
    from alm_orchestrator.config import Config

    config = Config.from_env()
    daemon = Daemon(config)

    # Verify ClaudeExecutor was called with profiles_dir
    mock_executor_class.assert_called_once()
    call_kwargs = mock_executor_class.call_args[1]
    assert "profiles_dir" in call_kwargs
    assert "sandbox" in call_kwargs["profiles_dir"]
```

**Step 3: Run test to verify it fails**

```bash
source .venv/bin/activate && pytest tests/test_daemon.py::test_daemon_initializes_executor_with_profiles_dir -v
```

Expected: FAIL (profiles_dir not passed)

**Step 4: Modify daemon.py to pass profiles_dir**

Find the line that creates `ClaudeExecutor()` and update it:

```python
# Add import at top
from pathlib import Path

# In __init__ or wherever ClaudeExecutor is created:
prompts_dir = Path(__file__).parent.parent.parent / "prompts"
self._executor = ClaudeExecutor(
    profiles_dir=str(prompts_dir / "sandbox")
)
```

**Step 5: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_daemon.py::test_daemon_initializes_executor_with_profiles_dir -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/alm_orchestrator/daemon.py tests/test_daemon.py
git commit -m "feat: configure daemon to use sandbox profiles"
```

---

## Task 5: Update Actions to Use Profiles

**Files:**
- Modify: `src/alm_orchestrator/actions/investigate.py`
- Modify: `src/alm_orchestrator/actions/impact.py`
- Modify: `src/alm_orchestrator/actions/recommend.py`
- Modify: `src/alm_orchestrator/actions/code_review.py`
- Modify: `src/alm_orchestrator/actions/security_review.py`
- Modify: `src/alm_orchestrator/actions/fix.py`
- Modify: `src/alm_orchestrator/actions/implement.py`

**Step 1: Update investigate.py**

Change:
```python
allowed_tools=ClaudeExecutor.TOOLS_READONLY,
```

To:
```python
profile="investigate",
```

Also remove the `ClaudeExecutor` import if no longer needed for `TOOLS_READONLY`.

**Step 2: Update impact.py, recommend.py, code_review.py, security_review.py**

Same change as investigate.py - replace `allowed_tools=ClaudeExecutor.TOOLS_READONLY` with `profile="investigate"`.

**Step 3: Update fix.py**

Change:
```python
allowed_tools=ClaudeExecutor.TOOLS_READWRITE,
```

To:
```python
profile="fix",
```

**Step 4: Update implement.py**

Change:
```python
allowed_tools=ClaudeExecutor.TOOLS_READWRITE,
```

To:
```python
profile="implement",
```

**Step 5: Run all action tests**

```bash
source .venv/bin/activate && pytest tests/test_actions/ -v
```

Expected: PASS (tests mock execute_with_template, so they don't care about the parameter name change)

**Step 6: Commit**

```bash
git add src/alm_orchestrator/actions/
git commit -m "refactor: switch actions from allowed_tools to sandbox profiles"
```

---

## Task 6: Update Action Tests to Verify Profile Usage

**Files:**
- Modify: `tests/test_actions/test_investigate.py`
- Modify: `tests/test_actions/test_fix.py`

**Step 1: Update test_investigate.py to verify profile parameter**

In `test_execute_flow`, add assertion:

```python
# Verify profile was passed instead of allowed_tools
call_kwargs = mock_claude.execute_with_template.call_args[1]
assert call_kwargs.get("profile") == "investigate"
assert "allowed_tools" not in call_kwargs or call_kwargs.get("allowed_tools") is None
```

**Step 2: Run test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_actions/test_investigate.py::TestInvestigateAction::test_execute_flow -v
```

Expected: PASS

**Step 3: Update test_fix.py similarly**

Add assertion for `profile="fix"`.

**Step 4: Run all tests**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add tests/test_actions/
git commit -m "test: verify actions use correct sandbox profiles"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `docs/sandbox-profiles-design.md`
- Modify: `CLAUDE.md` (if needed)

**Step 1: Update design doc status**

Change status from "Draft" to "Implemented".

**Step 2: Add profile location to CLAUDE.md architecture section**

Add under Architecture:
```markdown
### Sandbox Profiles

Sandbox profiles in `prompts/sandbox/` control Claude Code permissions:
- `investigate.json` — Read-only, no network (analysis actions)
- `fix.json` — Read-write, no network (bug fixes)
- `implement.json` — Read-write, package registries allowed (new features)
```

**Step 3: Commit**

```bash
git add docs/ CLAUDE.md
git commit -m "docs: update sandbox profiles documentation"
```

---

## Task 8: Final Verification

**Step 1: Run full test suite**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: All PASS

**Step 2: Verify profile files are valid JSON**

```bash
python -c "import json; [json.load(open(f)) for f in ['prompts/sandbox/investigate.json', 'prompts/sandbox/fix.json', 'prompts/sandbox/implement.json']]"
```

Expected: No errors

**Step 3: Manual smoke test (optional)**

```bash
# Clone a test repo and verify sandbox is applied
cd /tmp
git clone https://github.com/some/test-repo test-repo
mkdir -p test-repo/.claude
cp /path/to/prompts/sandbox/investigate.json test-repo/.claude/settings.local.json
cd test-repo
claude -p "Run: curl --version" --output-format json
# Should show permission_denials for curl
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create sandbox profile JSONs | `prompts/sandbox/*.json` |
| 2 | Add profile installation to executor | `claude_executor.py` |
| 3 | Add executor edge case tests | `test_claude_executor.py` |
| 4 | Update daemon to pass profiles_dir | `daemon.py` |
| 5 | Switch actions to use profiles | `actions/*.py` |
| 6 | Update action tests | `test_actions/*.py` |
| 7 | Update documentation | `docs/`, `CLAUDE.md` |
| 8 | Final verification | N/A |

**Total commits:** 8
