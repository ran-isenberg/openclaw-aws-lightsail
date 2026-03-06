# CLAUDE.md

## Project Overview

OpenClaw on AWS Lightsail — a CDK (Python) project that deploys an [OpenClaw](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/) autonomous AI agent on Amazon Lightsail with a static IP, auto snapshots, and Amazon Bedrock as the default model provider.

## Tech Stack

- **Language**: Python 3.14+
- **IaC**: AWS CDK v2 (Python bindings via `aws-cdk-lib`)
- **Package manager**: [uv](https://docs.astral.sh/uv/) for Python deps, npm/npx for CDK CLI
- **Linting/Formatting**: Ruff (Python), markdownlint (Markdown)
- **Testing**: pytest with CDK assertion helpers (`aws_cdk.assertions`)
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) — runs lint, test, synth, and npm audit on PRs

## Repository Structure

```text
.
├── app.py                          # CDK app entry point (synthesizes OpenClawStack)
├── cdk/
│   ├── constants.py                # Shared config (REGION, overridable via env var)
│   ├── openclaw_stack.py           # Main stack: composes AiAgent construct, adds CfnOutputs
│   └── constructs/
│       └── ai_agent.py             # Domain construct: Lightsail instance + static IP + firewall
├── tests/
│   └── unit/
│       └── test_openclaw_stack.py  # Synthesis-time assertion tests (incl. security tests)
├── .github/
│   ├── workflows/ci.yml            # PR checks: lint + test + synth + npm audit
│   └── release.yml                 # Release changelog categories
├── Makefile                        # All dev commands (install, test, lint, deploy, etc.)
├── pyproject.toml                  # Python project config (deps, ruff, pytest)
├── package.json                    # CDK CLI + markdownlint version pins
├── cdk.json                        # CDK app command: "uv run python app.py"
└── .markdownlint.yaml              # Markdown lint rules
```

## Common Commands

All commands are in the `Makefile`:

```bash
make install       # Install all deps (uv sync --dev && npm install)
make test          # Run pytest: uv run pytest tests/ -v
make lint          # Ruff check + format check + markdownlint
make format        # Auto-fix: ruff check --fix + ruff format
make synth         # CDK synth (npx cdk synth)
make diff          # CDK diff
make deploy        # CDK deploy (--require-approval any-change)
make destroy       # CDK destroy (interactive confirmation required)
make update-deps   # Upgrade all deps (uv lock --upgrade, npm update)
make pr            # Pre-PR gate: lint + test + synth
```

**Before opening a PR, always run `make pr`** (runs lint, test, and synth).

## Code Conventions

### Python Style (enforced by Ruff)

- **Line length**: 150 characters max
- **Indent**: 4 spaces
- **Quote style**: single quotes
- **Import sorting**: isort with `aws_cdk` and `constructs` as known third-party
- **Target version**: Python 3.14
- **Lint rules enabled**: pycodestyle (E/W), pyflakes (F), isort (I), flake8-comprehensions (C), flake8-bugbear (B), pylint (PL)

### CDK Patterns

- **Domain-Driven Design (DDD) constructs**: organize constructs by business domain (e.g., `AiAgent`), not by AWS resource type. See `cdk/constructs/`.
- **Props as dataclasses**: use `@dataclass` for construct props (see `AiAgentProps`).
- **Single stack**: one repo, one CDK app, one stack (`OpenClawStack`).
- **Constants**: shared config values live in `cdk/constants.py`. Region is overridable via `CDK_DEFAULT_REGION` env var.
- **Stack-level names**: instance and static IP names are defined at the stack level in `openclaw_stack.py`, not inside constructs.

### Testing

- Tests use CDK `Template.from_stack()` and assertion methods like `has_resource_properties` and `resource_count_is`.
- Test classes are grouped by domain: `TestAiAgent` (instance properties), `TestAiAgentNetworking` (static IP), `TestSecurity` (firewall, tags, resource inventory).
- Helper `_create_template()` creates a fresh stack per test.
- No mocking — tests validate the synthesized CloudFormation template directly.

### Git & PR Workflow

- Default branch: `main`
- CI runs on every PR: lint, test, CDK synth, npm audit (`.github/workflows/ci.yml`)
- Release changelog categories defined in `.github/release.yml` (breaking-change, enhancement, bug, documentation, chore, dependencies)
- Lock files (`uv.lock`, `package-lock.json`) are committed to ensure reproducible builds

## Security Conventions

- **Firewall rules are explicit**: every Lightsail instance must have a `networking` property with explicit port rules. Never rely on blueprint defaults. See `ai_agent.py` for the pattern.
- **Termination protection**: enabled on the stack to prevent accidental deletion.
- **Deploy approval**: `--require-approval any-change` — CDK prompts for all changes, not just security-group-widening.
- **Destroy safety**: `make destroy` requires interactive `yes` confirmation; no `--force` flag.
- **Account pinning**: `CDK_DEFAULT_ACCOUNT` env var is read in `app.py` to prevent deploying to the wrong account.
- **Dependency pinning**: all deps have upper bounds. Lock files are committed for reproducible builds.
- **Resource tags**: `Project` and `ManagedBy` tags are applied at the app level in `app.py`.
- **Security tests**: `TestSecurity` class validates firewall rules, resource inventory, and tag presence.
- **Accepted risks** (documented, not fixable in CDK):
    - Lightsail snapshots use AWS-managed encryption only (no customer-managed KMS support).
    - Single-AZ deployment by design for cost optimization; auto-snapshots enable recovery.

## Key Files to Know

| File | Purpose |
|------|---------|
| `cdk/constructs/ai_agent.py` | Core construct — Lightsail instance + static IP + firewall |
| `cdk/openclaw_stack.py` | Stack composition and CfnOutputs |
| `cdk/constants.py` | Region config (default `us-east-1`, override via `CDK_DEFAULT_REGION`) |
| `tests/unit/test_openclaw_stack.py` | All unit tests including security assertions |
| `pyproject.toml` | Python deps, ruff config, pytest config |
| `.github/workflows/ci.yml` | CI pipeline for PRs |

## Important Notes

- The CDK app is invoked via `uv run python app.py` (configured in `cdk.json`).
- The OpenClaw Lightsail blueprint (`openclaw_ls_1_0`) must exist in the target region before deploying.
- Firewall rules are defined in `ai_agent.py` — update `SSH_ALLOWED_CIDRS` to restrict SSH access before deploying to production.
- Auto snapshots are enabled by default at 04:00 UTC.
- The static IP depends on the Lightsail instance (`add_dependency`).
