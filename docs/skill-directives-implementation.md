# Skill Directives Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable Claude Code CLI to use superpowers skills in headless mode by adding directive headers to prompt templates and enabling the plugin in settings files.

**Prerequisite:** Complete sandbox-profiles-implementation.md first (creates the `prompts/*.json` settings files).

**Skill Mapping (Minimal Set):**

| Action | Skill | Purpose |
|--------|-------|---------|
| `investigate` | `systematic-debugging` | Four-phase debugging framework |
| `fix` | `test-driven-development` | Write failing test, then fix |
| `implement` | `test-driven-development` | Write failing tests, then implement |

---

## Task 1: Update Settings JSON Files

**Files:**
- Modify: `prompts/investigate.json`
- Modify: `prompts/impact.json`
- Modify: `prompts/recommend.json`
- Modify: `prompts/code_review.json`
- Modify: `prompts/security_review.json`
- Modify: `prompts/fix.json`
- Modify: `prompts/implement.json`

**Step 1: Add Skill permission and enabledPlugins to investigate.json**

Add `"Skill(*)"` as the first item in the `allow` array, and add the `enabledPlugins` section after `permissions`:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Skill(*)",
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
  },
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  }
}
```

**Step 2: Apply same changes to impact.json**

Add `"Skill(*)"` to allow array and `enabledPlugins` section (same content as investigate.json).

**Step 3: Apply same changes to recommend.json**

Add `"Skill(*)"` to allow array and `enabledPlugins` section (same content as investigate.json).

**Step 4: Apply same changes to code_review.json**

Add `"Skill(*)"` to allow array and `enabledPlugins` section (same content as investigate.json).

**Step 5: Apply same changes to security_review.json**

Add `"Skill(*)"` to allow array and `enabledPlugins` section (same content as investigate.json).

**Step 6: Update fix.json**

Add `"Skill(*)"` as the first item in the `allow` array, and add the `enabledPlugins` section:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Skill(*)",
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git:*)",
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
      "Bash(make:*)",
      "Bash(cmake:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(pip3:*)",
      "Bash(npm test:*)",
      "Bash(npm run:*)",
      "Bash(npx:*)",
      "Bash(node:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(mvn:*)",
      "Bash(./mvnw:*)",
      "Bash(gradle:*)",
      "Bash(./gradlew:*)",
      "Bash(java:*)",
      "Bash(javac:*)",
      "Bash(jar:*)",
      "Bash(go:*)",
      "Bash(cargo:*)",
      "Bash(rustc:*)"
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
  },
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  }
}
```

**Step 7: Update implement.json**

Add `"Skill(*)"` as the first item in the `allow` array, and add the `enabledPlugins` section:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false
  },
  "permissions": {
    "allow": [
      "Skill(*)",
      "Read(**)",
      "Write(**)",
      "Edit(**)",
      "Glob(**)",
      "Grep(**)",
      "Bash(git:*)",
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
      "Bash(make:*)",
      "Bash(cmake:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(python3:*)",
      "Bash(pip:*)",
      "Bash(pip3:*)",
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(node:*)",
      "Bash(yarn:*)",
      "Bash(pnpm:*)",
      "Bash(mvn:*)",
      "Bash(./mvnw:*)",
      "Bash(gradle:*)",
      "Bash(./gradlew:*)",
      "Bash(java:*)",
      "Bash(javac:*)",
      "Bash(jar:*)",
      "Bash(go:*)",
      "Bash(cargo:*)",
      "Bash(rustc:*)",
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
  },
  "enabledPlugins": {
    "superpowers@superpowers-marketplace": true
  }
}
```

**Step 8: Validate JSON syntax**

```bash
python -c "import json; [json.load(open(f'prompts/{a}.json')) for a in ['investigate', 'impact', 'recommend', 'code_review', 'security_review', 'fix', 'implement']]"
```

Expected: No errors

**Step 9: Commit**

```bash
git add prompts/*.json
git commit -m "feat: enable superpowers plugin in sandbox settings"
```

---

## Task 2: Add Skill Directives to Prompt Templates

**Files:**
- Modify: `prompts/investigate.md`
- Modify: `prompts/fix.md`
- Modify: `prompts/implement.md`

**Step 1: Add directive header to investigate.md**

Add the following line at the very top of the file, before `# Root Cause Investigation`:

```markdown
> **For Claude:** Use superpowers:systematic-debugging to investigate this issue. Follow the four-phase framework: root cause investigation, pattern analysis, hypothesis testing, then findings.

```

(Note: Include a blank line after the directive)

**Step 2: Add directive header to fix.md**

Add the following line at the very top of the file, before `# Bug Fix Implementation`:

```markdown
> **For Claude:** Use superpowers:test-driven-development for this fix. Write a failing test first, then implement the minimal fix to make it pass.

```

**Step 3: Add directive header to implement.md**

Add the following line at the very top of the file, before `# Feature Implementation`:

```markdown
> **For Claude:** Use superpowers:test-driven-development for this implementation. Write failing tests first, then implement to make them pass.

```

**Step 4: Commit**

```bash
git add prompts/*.md
git commit -m "feat: add skill directive headers to prompt templates"
```

---

## Task 3: Verification

**Step 1: Validate JSON syntax**

```bash
python -c "import json; [json.load(open(f'prompts/{a}.json')) for a in ['investigate', 'impact', 'recommend', 'code_review', 'security_review', 'fix', 'implement']]"
```

Expected: No errors

**Step 2: Smoke test skill invocation (optional)**

Test that Claude can access the skill in headless mode:

```bash
# Create a temp directory with settings
mkdir -p /tmp/skill-test/.claude
cp prompts/investigate.json /tmp/skill-test/.claude/settings.local.json
cd /tmp/skill-test
git init

# Test skill access
claude -p "Use the Skill tool to read superpowers:systematic-debugging and confirm you can access it. Reply with just 'SUCCESS' or 'FAILED'." --output-format json
```

Expected: Response contains "SUCCESS" and no permission_denials for Skill tool

**Step 3: Verify no permission denials**

Check the JSON output from Step 2:
- `permission_denials` should be an empty array `[]`
- If Skill is denied, check that `"Skill(*)"` is in the allow list

---

## Summary

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1 | Enable superpowers plugin in settings | `prompts/*.json` (7 files) | `feat: enable superpowers plugin in sandbox settings` |
| 2 | Add skill directive headers | `prompts/*.md` (3 files) | `feat: add skill directive headers to prompt templates` |
| 3 | Verification | N/A | (none) |

**Total commits:** 2

**Key points:**
- All 7 settings files get `Skill(*)` and `enabledPlugins` for consistency
- Only 3 prompt templates get directive headers (minimal skill set)
- Other templates (`impact`, `recommend`, `code_review`, `security_review`) can add directives later if needed
