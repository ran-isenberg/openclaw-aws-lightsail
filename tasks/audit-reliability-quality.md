# Reliability & Code Quality Audit

**Date:** 2026-03-06
**Scope:** All source files in `cdk/`, `tests/`, `app.py`, `.github/workflows/ci.yml`, `pyproject.toml`, `Makefile`, `package.json`, `cdk.json`

---

## Critical

### CRIT-1: SSH firewall defaults to `0.0.0.0/0`

**File:** `cdk/constructs/ai_agent.py:16`

```python
SSH_ALLOWED_CIDRS = ['0.0.0.0/0']  # ships open to the internet
```

The module-level default is world-open SSH. A deployer who forgets to update it gets an internet-exposed port 22 with no warning. The Lightsail instance runs an AI agent with Bedrock access — a hijacked instance incurs immediate API cost.

**Fix options:**

- Remove SSH from `DEFAULT_FIREWALL_RULES` entirely; require callers to opt in.
- Use a documentation CIDR (`192.0.2.0/24`) so connectivity fails loudly instead of silently permitting access.
- Add a `cdk.Annotations.of(self).add_warning()` at synthesis time if `0.0.0.0/0` is still present.

---

## High

### HIGH-1: No test asserting SSH is CIDR-restricted

**File:** `tests/unit/test_openclaw_stack.py`

`test_firewall_includes_ssh` only asserts port 22 exists — it does not check the CIDR. Removing SSH CIDR restrictions would pass CI silently.

**Fix:** Add a negative assertion:

```python
def test_ssh_is_not_open_to_world(self):
    resources = template.to_json()['Resources']
    for resource in resources.values():
        if resource['Type'] != 'AWS::Lightsail::Instance':
            continue
        for port in resource['Properties']['Networking']['Ports']:
            if port.get('FromPort') == 22:
                assert '0.0.0.0/0' not in port.get('Cidrs', [])
```

### HIGH-2: Duplicate port-443 test assertions

**File:** `tests/unit/test_openclaw_stack.py:68–100`

`test_instance_has_firewall_rules` and `test_firewall_includes_https` assert identical conditions (port 443/tcp). One is a strict subset of the other; both pass while testing nothing different.

**Fix:** Remove `test_instance_has_firewall_rules`; rename and strengthen `test_firewall_includes_https` to assert all three fields including `Cidrs`.

### HIGH-3: Snapshot time hardcoded, not a configurable prop

**File:** `cdk/constructs/ai_agent.py:55`

```python
snapshot_time_of_day='04:00'  # no override path
```

`AiAgentProps` exposes `enable_auto_snapshot: bool` but not the time. The value is untestable and non-overridable.

**Fix:** Add `snapshot_time_of_day: str = '04:00'` to `AiAgentProps` and reference it in the construct.

### HIGH-4: No monitoring or alerting

**Architectural gap**

There are no CloudWatch alarms, SNS topics, or health checks. If the Lightsail instance crashes or OpenClaw stops responding, detection and recovery are entirely manual.

**Fix:** Add a CloudWatch alarm on instance status checks, or at minimum document the expected recovery procedure (snapshot restore) with estimated RTO.

---

## Medium

### MED-1: `firewall_rules` is untyped `list[dict]`

**File:** `cdk/constructs/ai_agent.py:18,32`

Dictionary keys (`protocol`, `from_port`, `to_port`, `cidrs`) are unvalidated. Errors surface only at CDK synthesis time. Given the security importance of firewall rules, a `TypedDict` or dataclass catches mistakes at definition time.

**Fix:**

```python
from typing import TypedDict

class FirewallRule(TypedDict, total=False):
    protocol: str
    from_port: int
    to_port: int
    cidrs: list[str]
```

### MED-2: `attached_to` uses a plain string, not a CDK token reference

**File:** `cdk/constructs/ai_agent.py:87`

```python
attached_to=props.instance_name,  # string literal, not a token
```

`self.instance.ref` would create a hard CloudFormation dependency that resolves correctly regardless of naming changes. The current approach can silently drift if the instance name changes through a CDK transform.

**Fix:** `attached_to=self.instance.ref`

### MED-3: `availability_zone` breaks with environment-agnostic deploy

**File:** `cdk/openclaw_stack.py:14`

```python
availability_zone = f'{self.region}a'
```

When `env` is not passed, `self.region` resolves to the CDK token `AWS::Region`, making the f-string a token concatenation that `CfnInstance.availability_zone` may not handle correctly. Safe today because `app.py` always passes a concrete region, but fragile.

**Fix:** Add an optional `availability_zone` to `AiAgentProps` with `{region}a` as the documented default; document the assumption.

### MED-4: No test for `enable_auto_snapshot=False` branch

**File:** `cdk/constructs/ai_agent.py:49–58`

The branch that passes `add_ons=None` is never exercised. A regression in `if add_ons else None` would go undetected.

**Fix:** Add a test that creates an `AiAgent` with `enable_auto_snapshot=False` and asserts `AddOns` is absent.

### MED-5: No test for custom `firewall_rules` override

**File:** `tests/unit/test_openclaw_stack.py`

`AiAgentProps.firewall_rules` is designed to be overridable but no test verifies the dict-to-`PortProperty` mapping for non-default rules, including the `cidrs` fallback via `rule.get('cidrs', ['0.0.0.0/0'])` at `ai_agent.py:65`.

### MED-6: `ManagedBy` tag is never asserted in tests

**File:** `tests/unit/test_openclaw_stack.py:129–143`

`test_tags_are_applied` checks `Project` only. Removal of `ManagedBy: CDK` from `app.py` would pass CI.

### MED-7: CI skipped on direct push to `main`

**File:** `.github/workflows/ci.yml:3–5`

```yaml
on:
  pull_request:
    branches: [main]
```

Emergency or administrative pushes directly to `main` bypass lint, test, and synth entirely.

**Fix:** Add `on: push: branches: [main]`.

### MED-8: No Python version pin in CI

**File:** `.github/workflows/ci.yml:21`

`astral-sh/setup-uv@v5` has no `python-version`. The runner's default Python might not be 3.14, causing tests to run on the wrong interpreter silently.

**Fix:**

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    python-version: '3.14'
```

### MED-9: No `context` block in `cdk.json`

**File:** `cdk.json`

CDK feature flags are entirely absent. `cdk synth` may emit warnings about unacknowledged context keys that are silently swallowed in CI. Without explicit flags, CDK version bumps can silently change behavior.

**Fix:** Run `npx cdk acknowledge` and commit the resulting `context` block.

---

## Low

### LOW-1: `E501` suppressed alongside `line-length = 150`

**File:** `pyproject.toml:64`

`E501` is in the `ignore` list, so the linter never enforces line length — only the formatter does. `ruff check` gives a clean result even on unformatted overlong lines.

**Fix:** Remove `E501` from `ignore`; it is already bounded by `line-length = 150`.

### LOW-2: GitHub Actions use floating tag refs, not SHA-pinned

**File:** `.github/workflows/ci.yml:14,16,21`

`actions/checkout@v4`, `actions/setup-node@v4`, `astral-sh/setup-uv@v5` can be silently redirected by a tag mutation (supply-chain attack vector).

**Fix:** Pin each action to a commit SHA.

### LOW-3: `test_resource_count` duplicates assertions in `test_no_unexpected_resource_types`

**File:** `tests/unit/test_openclaw_stack.py:61–64,119–127`

Both tests assert `resource_count_is` for the same two resource types. The `TestSecurity` version is strictly stronger (also checks no other types exist). `test_resource_count` should be removed.

### LOW-4: Snapshot time constant not in `constants.py`

**File:** `cdk/constructs/ai_agent.py:8–12`

`OPENCLAW_BLUEPRINT_ID` and `DEFAULT_BUNDLE_ID` live in `ai_agent.py` while `REGION` lives in `cdk/constants.py`. Someone looking for "all tunable defaults" must check two files.

### LOW-5: `markdownlint-cli` uses `^` range while `aws-cdk` is pinned exactly

**File:** `package.json:6`

Inconsistent pinning philosophy. The `package-lock.json` mitigates this in practice but contradicts the stated policy of reproducible builds.

### LOW-6: `DashboardUrl` output gives no actionable pairing instructions

**File:** `cdk/openclaw_stack.py:26–31`

The description warns about IP-based HTTPS and SSH pairing but gives no steps. A first-time operator has no path forward from this output alone.

---

## Prioritised Remediation Order

| # | Severity | Finding | Effort |
|---|----------|---------|--------|
| 1 | Critical | SSH defaults to `0.0.0.0/0` (CRIT-1) | Low |
| 2 | High | No SSH CIDR restriction test (HIGH-1) | Low |
| 3 | High | Snapshot time hardcoded (HIGH-3) | Low |
| 4 | Medium | `attached_to` string vs token ref (MED-2) | Low |
| 5 | Medium | Python version missing in CI (MED-8) | Trivial |
| 6 | High | Duplicate HTTPS test assertions (HIGH-2) | Trivial |
| 7 | Medium | CI skipped on push to main (MED-7) | Trivial |
| 8 | Medium | No test for `enable_auto_snapshot=False` (MED-4) | Medium |
| 9 | Medium | Untyped `firewall_rules` (MED-1) | Medium |
| 10 | Medium | No test for custom firewall rule overrides (MED-5) | Medium |
| 11 | Medium | `ManagedBy` tag untested (MED-6) | Trivial |
| 12 | Medium | No `context` block in `cdk.json` (MED-9) | Low |
| 13 | Medium | `availability_zone` token issue (MED-3) | Medium |
| 14 | High | No monitoring/alerting (HIGH-4) | High |
| 15 | Low | Remaining LOW items | Trivial–Low |
