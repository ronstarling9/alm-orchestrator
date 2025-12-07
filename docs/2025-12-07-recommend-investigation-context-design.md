# Design: Include Investigation Results in Recommend Action

## Overview

The `ai-recommend` action should include prior investigation results (from `ai-investigate`) as context when generating recommendations. Investigation results are optional—recommend works standalone but produces better results with investigation context.

## Identifying Investigation Comments

Comments are identified as investigation results when:
1. The comment author matches the service account's Jira account ID
2. The comment body starts with `"INVESTIGATION RESULTS"`

Only the most recent matching comment is used.

## Changes

### JiraClient: Service Account Identity

Fetch and cache the service account's Jira account ID at startup.

- Add `_account_id: Optional[str]` instance variable
- Add `_fetch_account_id()` that calls `jira.myself()` and logs at DEBUG: `"Service account ID: {account_id}"`
- Call `_fetch_account_id()` during `__init__`
- Add public `account_id` property for read access

### JiraClient: get_comments() Return Type

Change return type from `List[str]` to `List[dict]`.

Each dict contains:
- `body`: Comment text
- `author_id`: Jira account ID of the author
- `created`: Timestamp string

### JiraClient: New get_investigation_comment() Method

```python
def get_investigation_comment(self, issue_key: str) -> Optional[str]:
```

Logic:
1. Call `get_comments(issue_key)` (already sorted newest-first)
2. Find first comment where `author_id == self.account_id` and `body.startswith("INVESTIGATION RESULTS")`
3. Return the body, or `None` if not found

### Update Existing get_comments() Callers

`code_review.py` and `security_review.py` pass comments to `find_pr_in_texts()`, which expects `List[str]`.

Fix: Extract bodies before passing:
```python
comments = jira_client.get_comments(issue_key)
comment_bodies = [c["body"] for c in comments]
pr_number = find_pr_in_texts(description, comment_bodies)
```

### RecommendAction: Fetch and Include Investigation Context

In `execute()`:
1. Call `jira_client.get_investigation_comment(issue_key)`
2. If `None`: log at DEBUG `"No investigation comment found for {issue_key} from account {jira_client.account_id}"`
3. Build investigation section in Python:

```python
if investigation_comment:
    investigation_section = (
        "## Prior Investigation\n\n"
        "The following investigation was already performed on this issue:\n\n"
        f"{investigation_comment}"
    )
else:
    investigation_section = ""
```

4. Pass `investigation_section` to template context

### prompts/recommend.md

Add placeholder where investigation context belongs:
```
{investigation_section}
```

Empty string adds nothing; populated string includes the full section.

## Tests

**Update existing:**
- Tests for `get_comments()` — new return type and assertions
- Tests for `code_review` and `security_review` — mock new dict format

**Add new:**
- `JiraClient.get_investigation_comment()` — finding/not finding, author matching, header matching
- `JiraClient.account_id` property — fetched and cached
- `RecommendAction` — with and without investigation context
