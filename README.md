# OpenClaw on AWS Lightsail (CDK Python)

[![license](https://img.shields.io/github/license/ran-isenberg/openclaw-aws-lightsail)](https://github.com/ran-isenberg/openclaw-aws-lightsail/blob/main/LICENSE)
![PythonSupport](https://img.shields.io/static/v1?label=python&message=3.14&color=blue?style=flat-square&logo=python)
![version](https://img.shields.io/github/v/release/ran-isenberg/openclaw-aws-lightsail)
![issues](https://img.shields.io/github/issues/ran-isenberg/openclaw-aws-lightsail)
![stars](https://img.shields.io/github/stars/ran-isenberg/openclaw-aws-lightsail)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CDK](https://img.shields.io/badge/AWS_CDK-v2-orange?logo=amazonwebservices)](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Lightsail-blue?logo=amazonwebservices)](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/)

---

Deploy [OpenClaw](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/) on Amazon Lightsail using AWS CDK (Python).

**[AWS Blog Post](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/)** | **[CDK Best Practices](https://ranthebuilder.cloud/blog/aws-cdk-best-practices-from-the-trenches/)** | **[Blogs website](https://www.ranthebuilder.cloud)**
> **Contact details | <ran.isenberg@ranthebuilder.cloud>**

---

## **What is OpenClaw?**

[OpenClaw](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/) is an open-source autonomous AI agent that runs on your own server.
It connects to messaging platforms like Slack, Telegram, WhatsApp, and Discord.
OpenClaw features proactive task execution, multi-channel integration, and the ability to run code, manage files, and browse the web.

The Lightsail OpenClaw instance is pre-configured with:

- **Amazon Bedrock** as the default AI model provider (Claude Sonnet 4.6)
- **Built-in HTTPS** via Let's Encrypt (auto-provisioned)
- **Device pairing authentication** for secure browser access
- **Sandboxed agent sessions** for improved security posture
- **Messaging channel support**: Telegram, WhatsApp, Slack

## **Architecture**

```text
                    ┌──────────────────────────────────────┐
                    │          OpenClawStack                │
                    │                                       │
                    │  ┌─────────────────────────────────┐  │
                    │  │     AiAgent (Construct)          │  │
                    │  │                                  │  │
                    │  │  ┌───────────────────────────┐   │  │
                    │  │  │  Lightsail Instance        │   │  │
                    │  │  │  Blueprint: openclaw_ls    │   │  │
                    │  │  │  Bundle: medium_3_0 (4GB)  │   │  │
                    │  │  │  Auto Snapshots: enabled   │   │  │
                    │  │  └───────────────────────────┘   │  │
                    │  │                                  │  │
                    │  │  ┌───────────────────────────┐   │  │
                    │  │  │  Static IP                 │   │  │
                    │  │  │  Attached to instance      │   │  │
                    │  │  └───────────────────────────┘   │  │
                    │  └─────────────────────────────────┘  │
                    │                                       │
                    │  Outputs:                             │
                    │   - DashboardUrl (https://ip/overview) │
                    │   - SetupGuide (setup blog post URL)  │
                    └──────────────────────────────────────┘
```

## **Project Structure**

```text
.
├── app.py                          # CDK app entry point
├── cdk/
│   ├── constants.py                # Region and shared configuration
│   ├── openclaw_stack.py           # Single stack composing DDD constructs
│   └── constructs/
│       └── ai_agent.py             # OpenClaw Lightsail instance + Static IP
├── tests/
│   └── unit/
│       └── test_openclaw_stack.py  # Synthesis-time assertion tests
├── Makefile                        # Deploy, destroy, test, lint commands
├── pyproject.toml                  # Python project config (uv + ruff)
├── package.json                    # CDK CLI version (npx)
└── cdk.json                        # CDK app configuration
```

## **Prerequisites**

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node.js and npm (CDK CLI version pinned in `package.json`, used via `npx`)
- AWS account with Lightsail access
- Complete the [Bedrock FTU form](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) for Claude model access (once per account)
- Verify the OpenClaw blueprint exists in your region:

  ```bash
  aws lightsail get-blueprints --query "blueprints[?contains(blueprintId, 'openclaw')]"
  ```

## **Quick Start**

```bash
# Install dependencies
make install

# Preview changes
make diff

# Deploy
make deploy

# Run tests
make test

# Lint
make lint

# Update all dependencies to latest
make update-deps

# Run all checks before opening a PR (lint + test + synth)
make pr

# Tear down
make destroy
```

## **Post-Deployment Setup**

1. Open the Lightsail console and navigate to your `openclaw-agent` instance
2. Choose **Connect using SSH** in the Getting started tab
3. Copy the **gateway token** from the welcome message
4. Open the HTTPS dashboard URL (printed as stack output) and pair your browser with the token
5. Run the Bedrock permissions script via CloudShell (shown in the SSH welcome message)
6. Configure messaging channels: `openclaw channels add`

## **Configuration**

Edit [`cdk/openclaw_stack.py`](cdk/openclaw_stack.py) to customize:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `INSTANCE_NAME` | Lightsail instance name | `openclaw-agent` |
| `bundle_id` | Instance size | `medium_3_0` (4GB, $24/mo) |
| `availability_zone` | AZ for the instance | `{region}a` |
| `enable_auto_snapshot` | Daily auto snapshots | `True` |

Region is configured in [`cdk/constants.py`](cdk/constants.py).

## **Design Decisions**

| Decision | Rationale |
|----------|-----------|
| **DDD constructs** | Organized by business domain (`AiAgent`) not AWS resource type. See [CDK best practices](https://ranthebuilder.cloud/blog/aws-cdk-best-practices-from-the-trenches/) |
| **Single stack** | One repo, one app, one stack |
| **Auto snapshots** | Enabled by default for data protection |
| **Static IP** | Stable HTTPS endpoint across instance stop/start cycles |
| **Blueprint defaults** | Firewall/networking managed by the OpenClaw blueprint, not overridden |
| **uv + npx** | Python deps via uv, CDK CLI version pinned in `package.json` |
| **Ruff** | Linting and formatting with ruff |

## **References**

- [Introducing OpenClaw on Amazon Lightsail (AWS Blog)](https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/)
- [Get started with OpenClaw on Lightsail (AWS Docs)](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-quick-start-guide-openclaw.html)
- [AWS CDK Best Practices from the Trenches](https://ranthebuilder.cloud/blog/aws-cdk-best-practices-from-the-trenches/)
- [AWS CDK Lightsail CfnInstance](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lightsail/CfnInstance.html)

## **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
