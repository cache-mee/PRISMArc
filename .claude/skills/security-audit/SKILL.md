---
name: security-audit
description: Run OWASP-aligned, read-only deterministic security checks (dependency, secrets, configuration, mobile/Expo) over the application, normalize the results into structured findings, and render the report templates. Use before a security gate decision, or to establish whether a security claim is true.
---

# Security Audit

Normative rules: `.claude/STANDARDS.md`. This skill is a capability, not a workflow.

## Purpose

Turn the repository's actual state into structured, evidence-backed security
findings — via deterministic checks, not by reasoning over the whole codebase.

## When to use

- A security gate decision (PASS/WARN/BLOCK) is needed for the repository or a
  bounded change.
- A claim like "no secrets are committed" or "dependencies are clean" needs to
  be established rather than assumed.

## When not to use

- To fix what is found — that is `implementation`.
- To orchestrate Test/Developer/Reviewer around the result — that is the
  calling agent (Security, or a Lead).
- As a substitute for manual threat modelling or architecture review.

## Inputs

- Required: the scope — repository root, or a bounded path/file list.
- Optional: `--out` path for the JSON, `--report` path for the rendered Markdown.

## Procedure

1. Run the tool via its cross-OS launcher — same pattern as `tools/scope-check`:
   `.claude/skills/security-audit/scripts/security-audit [--path <scope>]
   [--out <findings.json>] [--report <report.md>]` on Linux/macOS, or
   `.claude\skills\security-audit\scripts\security-audit.cmd [...]` on Windows.
   The launcher finds whichever Python 3 the machine has; do not hardcode
   `python3` directly, since that name does not exist on Windows.
2. The tool runs each check (dependency audit, secrets, configuration, mobile),
   using an available scanner where one exists on `PATH`, and its own targeted
   deterministic checks otherwise. A scanner that isn't installed is recorded as
   **SKIPPED — tool unavailable**, never simulated.
3. Read the emitted `security-findings.json` (the machine-readable source of
   truth) rather than re-deriving findings by reading source files.
4. If `--report` was passed, the same run also rendered
   `templates/security-report.md`'s structure from that JSON — read the
   rendered file rather than re-authoring it.
5. Only open a specific source file directly when verifying one particular
   finding in depth (e.g. confirming a flagged line in context) — never to scan
   broadly; that is what the tool is for.

## Outputs

- `security-findings.json` — machine-readable findings, per
  `templates/security-findings.json`.
- `security-report.md` — human-readable report, per
  `templates/security-report.md`, mechanically rendered from the JSON.
- Per-check status (PASS/WARN/FAIL/SKIPPED) and the overall gate value
  (PASS/WARN/BLOCK) the tool computed.

## Validation

- The tool's exit code matches its own reported gate value (0 = PASS/WARN,
  1 = BLOCK, 2 = usage/tool error).
- Every finding in the JSON carries `file`, `evidence` and an OWASP tag; a
  finding missing these is a tool defect, not a valid result.
- No raw secret value appears anywhere in the JSON or the rendered report —
  only `<REDACTED>` markers.

## Evidence

The tool's stdout JSON, and the rendered report file, are the evidence — per
`.orchestration/schemas/evidence.md`. This skill MUST NOT summarise scanner
output from memory in place of the actual JSON, and MUST NOT convert a SKIPPED
check into a PASS.

## Failure handling

If the tool cannot run at all (interpreter missing, path invalid), report
*not validated* and the exact error — do not fall back to manual reasoning
about security posture. A check reported SKIPPED is recorded as skipped in the
findings, never silently dropped.

## Scope

Read-only. Produces findings and reports; never modifies application code,
dependencies, or configuration, and never installs a scanner it doesn't find.
Findings outside the declared scope are recorded, not chased.

## Tools

`.claude/skills/security-audit/scripts/security-audit` (`.cmd` on Windows),
wrapping `security-audit.py` — the single deterministic entry point (dependency
audit, secrets, configuration, mobile checks; normalizes, redacts,
deduplicates, and renders the templates). Native Bash to invoke it, Read to
inspect a specific flagged line when verifying a finding.

## References

- `templates/security-report.md` — human report structure.
- `templates/security-findings.json` — machine-readable structure.
- `references/owasp-checks.md` — OWASP category list and what this skill can
  and cannot detect from this repository.
