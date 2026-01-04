# Output Validator Design

Status: **Ready for Implementation**

## Goal

Scan Claude's responses before posting to Jira to detect leaked credentials and secrets.

## Scope

- Secret pattern detection (using Gitleaks patterns)
- High-entropy string detection (40+ chars, entropy > 4.5)
- Jira comments only (not GitHub PRs)

## Decisions

| Decision | Choice |
|----------|--------|
| Where to scan | Centralized `_post_validated_comment()` helper in `BaseAction` |
| On detection | Block + notify with detection type |
| Pattern source | Gitleaks (MIT License) |
| High-entropy threshold | 40+ chars, Shannon entropy > 4.5 |

## Architecture

### New File: `src/alm_orchestrator/output_validator.py`

```python
from dataclasses import dataclass
import math
import re

@dataclass
class ValidationResult:
    is_valid: bool
    failure_type: str | None  # "credential_detected" or "high_entropy_string"

# From Gitleaks config - https://github.com/gitleaks/gitleaks
CREDENTIAL_PATTERNS = [
    # AWS Access Token
    (r"\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b", "aws_access_token"),

    # Private Key (PEM format)
    (r"(?i)-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----", "private_key"),

    # JWT
    (r"\b(ey[a-zA-Z0-9]{17,}\.ey[a-zA-Z0-9\/\\_-]{17,}\.[a-zA-Z0-9\/\\_-]{10,})", "jwt"),

    # Generic API Key
    (r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]", "generic_api_key"),
]

class OutputValidator:
    def __init__(self):
        self._compiled_patterns = [
            (re.compile(pattern), name) for pattern, name in CREDENTIAL_PATTERNS
        ]

    def validate(self, text: str) -> ValidationResult:
        """Scan text for secrets and high-entropy strings."""
        # Check credential patterns
        for pattern, name in self._compiled_patterns:
            if pattern.search(text):
                return ValidationResult(is_valid=False, failure_type=f"credential_detected:{name}")

        # Check high-entropy strings
        if self._has_high_entropy_strings(text):
            return ValidationResult(is_valid=False, failure_type="high_entropy_string")

        return ValidationResult(is_valid=True, failure_type=None)

    def _has_high_entropy_strings(self, text: str) -> bool:
        """Check for suspicious random-looking strings (40+ chars)."""
        pattern = r"[a-zA-Z0-9+/=_\-]{40,}"

        for match in re.finditer(pattern, text):
            candidate = match.group()
            if self._calculate_shannon_entropy(candidate) > 4.5:
                return True
        return False

    @staticmethod
    def _calculate_shannon_entropy(s: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not s:
            return 0.0
        freq = {}
        for c in s:
            freq[c] = freq.get(c, 0) + 1
        length = len(s)
        return -sum((count/length) * math.log2(count/length) for count in freq.values())
```

### Modified: `src/alm_orchestrator/actions/base.py`

Add to `BaseAction`:

```python
from alm_orchestrator.output_validator import OutputValidator

class BaseAction(ABC):
    def __init__(self, prompts_dir: str):
        self._prompts_dir = prompts_dir
        self._validator = OutputValidator()

    def _post_validated_comment(
        self,
        jira_client,
        issue_key: str,
        content: str,
    ) -> bool:
        """Validate content and post to Jira if safe.

        Returns:
            True if posted successfully, False if blocked.
        """
        result = self._validator.validate(content)

        if not result.is_valid:
            logger.warning(f"Response blocked for {issue_key}: {result.failure_type}")
            jira_client.add_comment(
                issue_key,
                f"AI RESPONSE BLOCKED\n\n"
                f"Reason: {result.failure_type}\n\n"
                f"The AI agent's response was flagged by automated security checks "
                f"and has not been posted. Please review the issue manually."
            )
            return False

        jira_client.add_comment(issue_key, content)
        return True
```

## Implementation Plan

**Files to create:**
1. `src/alm_orchestrator/output_validator.py`

**Files to modify:**
2. `src/alm_orchestrator/actions/base.py`
3. Actions that post to Jira:
   - `actions/investigate.py`
   - `actions/impact.py`
   - `actions/recommend.py`
   - `actions/fix.py`
   - `actions/implement.py`
   - `actions/code_review.py`
   - `actions/security_review.py`

**Tests to create:**
4. `tests/test_output_validator.py`

**Order:**
1. Create `OutputValidator` with tests
2. Update `BaseAction`
3. Update actions one by one

## References

- [Gitleaks](https://github.com/gitleaks/gitleaks) - Source for credential patterns (MIT License)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
