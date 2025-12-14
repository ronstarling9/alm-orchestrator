# Issue Type Validation Design

## Overview

Add issue type validation to actions so each action only runs on appropriate Jira issue types. Invalid issue types are rejected with a clear comment.

## Requirements

| Action | Allowed Issue Types |
|--------|---------------------|
| `ai-investigate` | Bug |
| `ai-recommend` | Bug, Story |
| `ai-impact` | Bug, Story |
| `ai-fix` | Bug |
| `ai-implement` | Story |
| `ai-code-review` | Bug, Story |
| `ai-security-review` | Bug, Story |

All other issue types (Task, Epic, etc.) are rejected for all actions.

## Rejection Behavior

When an action runs on an invalid issue type:

1. Log a DEBUG message noting the rejection
2. Post a comment explaining the rejection
3. Remove the label so the issue isn't picked up again
4. Return early without invoking Claude

### Comment Format

```
INVALID ISSUE TYPE
==================

The ai-fix action only works on: Bug

This issue is a Story. Please use an appropriate action for this issue type.
```

## Implementation

### BaseAction Changes

Add `allowed_issue_types` property and `validate_issue_type()` method:

```python
@property
def allowed_issue_types(self) -> list[str]:
    """Issue types this action can run on. Override in subclasses."""
    return []  # Empty means no validation

def validate_issue_type(self, issue, jira_client) -> bool:
    """Check if issue type is allowed. Posts rejection comment if not.

    Args:
        issue: Jira issue object.
        jira_client: JiraClient for posting comments and removing labels.

    Returns:
        True if valid, False if rejected.
    """
    allowed = self.allowed_issue_types
    if not allowed:
        return True  # No validation configured

    issue_type = issue.fields.issuetype.name
    if issue_type in allowed:
        return True

    # Log rejection
    logger.debug(f"Rejecting {issue.key}: {self.label} does not support {issue_type}")

    # Post rejection comment
    allowed_str = ", ".join(allowed)
    header = "INVALID ISSUE TYPE"
    comment = (
        f"{header}\n"
        f"{'=' * len(header)}\n\n"
        f"The {self.label} action only works on: {allowed_str}\n\n"
        f"This issue is a {issue_type}. Please use an appropriate action for this issue type."
    )
    jira_client.add_comment(issue.key, comment)

    # Remove label
    jira_client.remove_label(issue.key, self.label)

    return False
```

### Per-Action Changes

Each action adds the `allowed_issue_types` property and calls validation at the start of `execute()`.

**investigate.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug"]

def execute(self, issue, jira_client, github_client, claude_executor) -> str:
    if not self.validate_issue_type(issue, jira_client):
        return f"Rejected {issue.key}: invalid issue type"
    # ... existing logic
```

**recommend.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug", "Story"]
```

**impact.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug", "Story"]
```

**fix.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug"]
```

**implement.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Story"]
```

**code_review.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug", "Story"]
```

**security_review.py:**
```python
@property
def allowed_issue_types(self) -> list[str]:
    return ["Bug", "Story"]
```

## Testing

### BaseAction Tests (test_base.py)

- `test_validate_issue_type_valid`: Valid type returns True, no comment posted
- `test_validate_issue_type_invalid`: Invalid type returns False, comment posted, label removed
- `test_validate_issue_type_empty_allowed`: Empty allowed list returns True (no validation)

### Per-Action Tests

Each action's test file verifies:
- `allowed_issue_types` returns correct list
- `execute()` on invalid type returns rejection message without invoking Claude

### Mock Structure

```python
mock_issue = MagicMock()
mock_issue.key = "TEST-123"
mock_issue.fields.issuetype.name = "Story"  # or "Bug"
```
