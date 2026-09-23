# aws-deploy-check

> @author Samson Paul, samson.paul@experionglobal.com

Deterministic, **read-only** AWS guardrails for the `aws` deployment
environment. Every subcommand runs a single read-only `aws` CLI call and
prints `PASS`/`FAIL` plus the supporting fact — it never creates, modifies or
destroys a resource, and it never prints a credential value.

Consumer: `.claude/agents/deploy.md`'s AWS deployment lifecycle. Each
subcommand is run twice per deploy — once at preflight/security-gate
(inspect before acting) and once at post-deploy verification (prove nothing
regressed) — which is the "inspect → reconcile → deploy → verify" idempotency
pattern, not a retry.

## Args

| Form | Behaviour |
|------|-----------|
| `aws-deploy-check identity --expected-account <id> --expected-region <region>` | Fails a deploy aimed at the wrong AWS account or region |
| `aws-deploy-check sg-open-check --group-id <sg-id> --port <port>` | Fails if any rule on that port allows `0.0.0.0/0` or `::/0` (used for the EC2 backend port and for SSH) |
| `aws-deploy-check s3-public-access --bucket <name>` | Fails unless all four S3 Block Public Access settings are on |
| `aws-deploy-check cloudfront-oac --distribution-id <id> --origin-id <origin-id>` | Fails unless that origin has an Origin Access Control and no legacy Origin Access Identity |
| `aws-deploy-check --help` | Show help |

## Running it, on any OS

| Platform | Launcher |
|---|---|
| Linux / macOS | `tools/aws-deploy-check/aws-deploy-check <subcommand> [args]` |
| Windows | `tools\aws-deploy-check\aws-deploy-check.cmd <subcommand> [args]` |

Requires the `aws` CLI to be installed and already authenticated (existing
credentials/profile/session) — this tool never handles or stores credentials
itself.

## Exits

| Code | Meaning |
|------|---------|
| 0 | PASS |
| 1 | FAIL — a real finding (wrong account/region, port open to the world, public S3 access, missing OAC) |
| 2 | Usage/error — `aws` CLI missing, the API call itself failed for a reason other than "no config found", or bad arguments |

## Smoke test (no AWS account required)

```sh
tools/aws-deploy-check/aws-deploy-check --help
# exit 0

tools/aws-deploy-check/aws-deploy-check identity --expected-account 111111111111 --expected-region us-east-1
# without the aws CLI installed:
# STOP: missing required command(s): aws
# exit 2  (fails closed rather than reporting a false PASS)
```
