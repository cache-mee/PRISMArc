#!/usr/bin/env python3
"""Read-only, OWASP-aligned security audit for salon-app.

Single deterministic entry point for the security-audit skill. Runs a small
set of checks (dependency vulnerabilities, secrets, security configuration,
mobile/Expo configuration), using an installed scanner where one exists and a
targeted regex-based check otherwise, then normalizes everything into the
skill's `templates/security-findings.json` shape. Never simulates a scanner
result, never modifies anything, never prints a raw secret value.

Usage:
  security-audit.py [--path <scope>] [--out <findings.json>] [--report <report.md>]
  security-audit.py --help

EXIT:
  0  gate PASS or WARN (non-blocking)
  1  gate BLOCK
  2  usage/tool error

@author Samson Paul, samson.paul@experionglobal.com
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools", "_lib"))
from common import banner, die, repo_root  # noqa: E402

EXCLUDE_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
    ".orchestration", ".next", "coverage",
}
TEXT_EXCLUDE_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".lock",
)

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

SECRET_PATTERNS = [
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}"), "HIGH", "HIGH",
     "AWS Access Key ID pattern detected"),
    ("private-key-header", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
     "CRITICAL", "HIGH", "Private key material detected"),
    ("slack-token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), "HIGH", "HIGH",
     "Slack token pattern detected"),
    ("generic-secret-assignment", re.compile(
        r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9/_\.\-]{8,}['\"]"),
     "MEDIUM", "MEDIUM", "Credential-like assignment detected"),
]

INSECURE_URL_RE = re.compile(r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[A-Za-z0-9.\-]+")
WEAK_CRYPTO_RE = re.compile(r"\b(md5|sha1)\s*\(")
CORS_WILDCARD_RE = re.compile(r"Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"]\*['\"]")
DEBUG_FLAG_RE = re.compile(r"(?i)\bdebug\b\s*[:=]\s*(true|1)\b")
DANGEROUS_LOG_RE = re.compile(
    r"(?i)(console\.log|print)\s*\([^)]*\b(password|secret|token|api[_-]?key)\b")

CODE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".yml", ".yaml", ".env", ".config.js")

# .env-style KEY=VALUE lines (no quotes required, unlike SECRET_PATTERNS' generic
# assignment pattern) — this stack loads config via pydantic-settings from a plain
# `.env` file, so a real leak here would not be quoted.
ENV_KEY_RE = re.compile(r"(?i)^\s*([A-Z0-9_]*(?:SECRET|PASSWORD|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY)[A-Z0-9_]*)\s*=\s*(.+?)\s*$")
ENV_PLACEHOLDER_VALUES = {
    "", "changeme", "change_me", "xxx", "xxxx", "your_key_here", "replace_me",
    "todo", "fixme", "example", "password", "secret", "user", "test",
}
CONN_STRING_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*://([^:@/\s]+):([^@/\s]+)@")
ENV_FILENAME_RE = re.compile(r"^\.env(\..+)?$")


def _walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".git")]
        for name in filenames:
            if name.endswith(TEXT_EXCLUDE_SUFFIXES):
                continue
            yield os.path.join(dirpath, name)


def _read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except OSError:
        return None


def _rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _next_id(counter):
    counter["n"] += 1
    return f"SEC-{counter['n']:03d}"


def _add_secret_finding(findings, counter, root, path, line_no, label, severity, confidence):
    findings.append({
        "id": _next_id(counter),
        "severity": severity,
        "confidence": confidence,
        "owasp": "A02",
        "status": "OPEN",
        "file": _rel(root, path),
        "line": line_no,
        "evidence": f"{label}: <REDACTED>",
        "impact": "Committed credential material can be extracted from the "
                  "repository and used to access the represented system.",
        "recommendation": "Remove the value from source control, rotate the "
                          "credential, and load it from a secret store or "
                          "environment variable instead.",
    })


def check_secrets(root, counter):
    findings = []
    for path in _walk_files(root):
        text = _read_text(path)
        if text is None:
            continue
        is_env_file = ENV_FILENAME_RE.match(os.path.basename(path)) is not None
        for line_no, line in enumerate(text.splitlines(), start=1):
            matched = False
            for check_id, pattern, severity, confidence, label in SECRET_PATTERNS:
                if pattern.search(line):
                    _add_secret_finding(findings, counter, root, path, line_no, label,
                                        severity, confidence)
                    matched = True
                    break  # one match per line is enough signal
            if matched:
                continue

            conn_match = CONN_STRING_RE.search(line)
            if conn_match and conn_match.group(2).strip().lower() not in ENV_PLACEHOLDER_VALUES:
                _add_secret_finding(findings, counter, root, path, line_no,
                                    "Connection string with embedded credentials detected",
                                    "HIGH", "MEDIUM")
                continue

            # Unquoted `.env`-style KEY=VALUE — this stack (pydantic-settings) loads
            # config from a plain .env file, so a real leak here would not be quoted
            # like SECRET_PATTERNS' generic-secret-assignment pattern expects.
            if is_env_file:
                env_match = ENV_KEY_RE.match(line)
                if env_match and env_match.group(2).strip().lower() not in ENV_PLACEHOLDER_VALUES:
                    _add_secret_finding(findings, counter, root, path, line_no,
                                        f"Populated credential-like env var ({env_match.group(1)})",
                                        "HIGH", "MEDIUM")
    status = "WARN" if findings else "PASS"
    return findings, {"name": "secrets", "status": status, "tool": "built-in regex scan"}


def check_security_configuration(root, counter):
    findings = []
    rules = [
        (INSECURE_URL_RE, "A02", "MEDIUM", "MEDIUM",
         "Plaintext http:// URL to a non-local host",
         "Traffic to this endpoint is unencrypted and can be intercepted or tampered with.",
         "Use https:// for any non-local endpoint."),
        (WEAK_CRYPTO_RE, "A02", "MEDIUM", "HIGH",
         "Weak hash function (md5/sha1) used",
         "md5/sha1 are unsuitable for security-sensitive hashing (passwords, tokens, signatures).",
         "Use a modern algorithm appropriate to the purpose (e.g. bcrypt/argon2 for passwords, "
         "sha-256+ for integrity)."),
        (CORS_WILDCARD_RE, "A05", "MEDIUM", "HIGH",
         "Wildcard CORS origin configured",
         "Any origin can call this endpoint, which weakens same-origin protections.",
         "Restrict Access-Control-Allow-Origin to an explicit allow-list."),
        (DEBUG_FLAG_RE, "A05", "LOW", "MEDIUM",
         "Debug flag left enabled",
         "Debug mode can expose stack traces, internals, or verbose errors in production.",
         "Ensure debug is disabled in production configuration/build."),
        (DANGEROUS_LOG_RE, "A09", "MEDIUM", "LOW",
         "Secret-like value passed to a log/print call",
         "Sensitive values written to logs can leak via log aggregation or console output.",
         "Remove the sensitive value from the log statement, or mask it before logging."),
    ]
    any_file = False
    for path in _walk_files(root):
        if not path.endswith(CODE_SUFFIXES) and "app.json" not in path and "app.config" not in path:
            continue
        text = _read_text(path)
        if text is None:
            continue
        any_file = True
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern, owasp, severity, confidence, label, impact, rec in rules:
                if pattern.search(line):
                    findings.append({
                        "id": _next_id(counter),
                        "severity": severity,
                        "confidence": confidence,
                        "owasp": owasp,
                        "status": "OPEN",
                        "file": _rel(root, path),
                        "line": line_no,
                        "evidence": label,
                        "impact": impact,
                        "recommendation": rec,
                    })
    if not any_file:
        return findings, {"name": "security-configuration", "status": "SKIPPED",
                           "tool": "built-in regex scan"}, "no applicable source/config files found"
    status = "WARN" if findings else "PASS"
    return findings, {"name": "security-configuration", "status": status,
                       "tool": "built-in regex scan"}, None


def check_mobile_configuration(root, counter):
    candidates = []
    for name in ("app.json", "app.config.js", "app.config.ts"):
        for path in _walk_files(root):
            if os.path.basename(path) == name:
                candidates.append(path)
    if not candidates:
        return [], {"name": "mobile-configuration", "status": "SKIPPED", "tool": "built-in check"}, \
            "no Expo/React Native app config found"
    findings = []
    for path in candidates:
        text = _read_text(path) or ""
        if re.search(r'"usesCleartextTraffic"\s*:\s*true', text) or \
           re.search(r'"NSAllowsArbitraryLoads"\s*:\s*true', text):
            findings.append({
                "id": _next_id(counter),
                "severity": "HIGH",
                "confidence": "HIGH",
                "owasp": "A05",
                "status": "OPEN",
                "file": _rel(root, path),
                "line": 1,
                "evidence": "Cleartext traffic / arbitrary loads permitted in app config",
                "impact": "The app can send or receive unencrypted network traffic, exposing "
                          "data in transit.",
                "recommendation": "Disable usesCleartextTraffic / NSAllowsArbitraryLoads and use "
                                  "explicit, HTTPS-only domain exceptions if one is genuinely "
                                  "required.",
            })
    status = "WARN" if findings else "PASS"
    return findings, {"name": "mobile-configuration", "status": status, "tool": "built-in check"}, None


SECURITY_HEADER_NAMES = (
    "X-Frame-Options", "X-Content-Type-Options", "Content-Security-Policy",
    "Strict-Transport-Security",
)


def check_deployment_configuration(root, counter):
    dockerfiles = [p for p in _walk_files(root) if os.path.basename(p).startswith("Dockerfile")]
    web_configs = [p for p in _walk_files(root) if os.path.basename(p) == "nginx.conf"]
    if not dockerfiles and not web_configs:
        return [], {"name": "deployment-configuration", "status": "SKIPPED", "tool": "built-in check"}, \
            "no Dockerfile or nginx.conf found"

    findings = []
    for path in dockerfiles:
        text = _read_text(path) or ""
        if not re.search(r"(?im)^\s*USER\s+\S+", text):
            findings.append({
                "id": _next_id(counter), "severity": "LOW", "confidence": "MEDIUM",
                "owasp": "A05", "status": "OPEN", "file": _rel(root, path), "line": 1,
                "evidence": "No USER instruction — container runs as root by default",
                "impact": "A container compromise gets root inside the container, widening "
                          "the blast radius of any other vulnerability.",
                "recommendation": "Add a non-root USER instruction before the final CMD/ENTRYPOINT.",
            })
    for path in web_configs:
        text = _read_text(path) or ""
        missing = [h for h in SECURITY_HEADER_NAMES if h.lower() not in text.lower()]
        if len(missing) == len(SECURITY_HEADER_NAMES):
            findings.append({
                "id": _next_id(counter), "severity": "LOW", "confidence": "MEDIUM",
                "owasp": "A05", "status": "OPEN", "file": _rel(root, path), "line": 1,
                "evidence": "No common security headers (X-Frame-Options, "
                            "X-Content-Type-Options, CSP, HSTS) configured",
                "impact": "Browsers fall back to permissive defaults, weakening protection "
                          "against clickjacking, MIME-sniffing and downgrade attacks.",
                "recommendation": "Add the missing headers in the server block (or at the "
                                  "reverse proxy in front of it).",
            })
    status = "WARN" if findings else "PASS"
    return findings, {"name": "deployment-configuration", "status": status,
                       "tool": "built-in check"}, None


def _run(cmd, cwd):
    # shutil.which resolves platform shims (e.g. npm.cmd on Windows) that a bare
    # name would not; subprocess with shell=False cannot find those on its own.
    exe = shutil.which(cmd[0])
    if not exe:
        return None, ""
    try:
        result = subprocess.run([exe, *cmd[1:]], cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, timeout=120)
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def _npm_severity_counts(audit_json):
    try:
        data = json.loads(audit_json)
    except (json.JSONDecodeError, TypeError):
        return None
    counts = {k: 0 for k in SEVERITY_ORDER}
    vulns = data.get("vulnerabilities")
    if isinstance(vulns, dict):
        for entry in vulns.values():
            sev = str(entry.get("severity", "")).lower()
            if sev == "moderate":
                sev = "medium"
            if sev in counts:
                counts[sev] += 1
        return counts
    return None


def _pip_audit_severity_counts(audit_json):
    try:
        data = json.loads(audit_json)
    except (json.JSONDecodeError, TypeError):
        return None
    deps = data.get("dependencies") if isinstance(data, dict) else data
    if not isinstance(deps, list):
        return None
    counts = {k: 0 for k in SEVERITY_ORDER}
    for dep in deps:
        for vuln in dep.get("vulns", []) or []:
            # pip-audit's advisory feed rarely carries a severity rating; a real,
            # unrated vulnerability is treated as MEDIUM rather than dropped.
            counts["medium"] += 1
    return counts


def check_dependency_audit(root, counter):
    node_dirs, python_dirs = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        if "package-lock.json" in filenames or "pnpm-lock.yaml" in filenames:
            node_dirs.append(dirpath)
        if "requirements.txt" in filenames or "pyproject.toml" in filenames:
            python_dirs.append(dirpath)

    if not node_dirs and not python_dirs:
        return [], {"name": "dependency-audit", "status": "SKIPPED", "tool": "n/a"}, \
            "no dependency manifest found (package-lock.json, pnpm-lock.yaml, " \
            "requirements.txt or pyproject.toml)"

    findings = []
    tools_used = []
    unavailable = []

    for d in node_dirs:
        use_pnpm = os.path.isfile(os.path.join(d, "pnpm-lock.yaml"))
        tool_name = "pnpm" if use_pnpm else "npm"
        rc, out = _run([tool_name, "audit", "--json"], cwd=d)
        if rc is None:
            unavailable.append(tool_name)
            continue
        tools_used.append(tool_name)
        counts = _npm_severity_counts(out) or {}
        for sev in SEVERITY_ORDER[:4]:
            if counts.get(sev):
                findings.append({
                    "id": _next_id(counter), "severity": sev.upper(), "confidence": "HIGH",
                    "owasp": "A06", "status": "OPEN",
                    "file": _rel(root, os.path.join(d, "package.json")), "line": 1,
                    "evidence": f"{counts[sev]} {sev}-severity advisory finding(s) reported by "
                                f"{tool_name} audit",
                    "impact": "A known vulnerability exists in a declared dependency.",
                    "recommendation": "Review the advisory and update the affected package to a "
                                      "patched version.",
                })

    for d in python_dirs:
        rc, out = _run(["pip-audit", "--format", "json", "--progress-spinner", "off"], cwd=d)
        if rc is None:
            unavailable.append("pip-audit")
            continue
        tools_used.append("pip-audit")
        counts = _pip_audit_severity_counts(out) or {}
        if counts.get("medium"):
            manifest = "pyproject.toml" if os.path.isfile(os.path.join(d, "pyproject.toml")) \
                else "requirements.txt"
            findings.append({
                "id": _next_id(counter), "severity": "MEDIUM", "confidence": "HIGH",
                "owasp": "A06", "status": "OPEN",
                "file": _rel(root, os.path.join(d, manifest)), "line": 1,
                "evidence": f"{counts['medium']} advisory finding(s) reported by pip-audit",
                "impact": "A known vulnerability exists in a declared dependency.",
                "recommendation": "Review the advisory and update the affected package to a "
                                  "patched version.",
            })

    if not tools_used:
        reason = f"tool unavailable ({', '.join(sorted(set(unavailable)))})" if unavailable \
            else "tool unavailable"
        return [], {"name": "dependency-audit", "status": "SKIPPED", "tool": "n/a"}, reason

    status = "WARN" if findings else "PASS"
    return findings, {"name": "dependency-audit", "status": status,
                       "tool": "/".join(sorted(set(tools_used)))}, None


OWASP_AREAS = [
    ("A01", "Broken Access Control", "N/A"),
    ("A02", "Cryptographic Failures", "CHECKED"),
    ("A03", "Injection", "NOT_CHECKED"),
    ("A04", "Insecure Design", "N/A"),
    ("A05", "Security Misconfiguration", "CHECKED"),
    ("A06", "Vulnerable Components", None),  # depends on dependency-audit having run
    ("A07", "Authentication Failures", "N/A"),
    ("A08", "Software/Data Integrity", "N/A"),
    ("A09", "Logging/Monitoring", "CHECKED"),
    ("A10", "SSRF", "N/A"),
]


def gate_from_summary(summary):
    if summary["critical"] > 0:
        return "BLOCK", "At least one CRITICAL finding is open."
    if summary["high"] > 0:
        return "BLOCK", "At least one HIGH-severity finding is open."
    if summary["medium"] > 0 or summary["low"] > 0:
        return "WARN", "Only MEDIUM/LOW findings are open."
    return "PASS", "No findings above informational severity."


def render_markdown(results):
    s = results["summary"]
    lines = [
        "# Security Audit Report", "",
        "## 1. Audit Summary", "",
        "| Field | Value |", "|---|---|",
        f"| Project | `{results['project']}` |",
        f"| Audit ID | `{results['audit_id']}` |",
        f"| Date | `{results['date']}` |",
        "| Auditor | `Security Agent` |",
        "| Mode | `READ-ONLY` |",
        f"| Result | `{results['status']}` |", "",
        "### Findings", "",
        "| Severity | Count |", "|---|---:|",
        f"| Critical | {s['critical']} |",
        f"| High | {s['high']} |",
        f"| Medium | {s['medium']} |",
        f"| Low | {s['low']} |",
        f"| Informational | {s['info']} |", "",
        "---", "", "## 2. Checks Performed", "",
        "| Check | Status | Tool |", "|---|---|---|",
    ]
    for c in results["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | `{c['tool']}` |")
    lines += ["", "---", "", "## 3. OWASP Coverage", "",
              "| OWASP Area | Status | Findings |", "|---|---|---:|"]
    dep_checked = any(c["name"] == "dependency-audit" and c["status"] != "SKIPPED"
                       for c in results["checks"])
    for code, label, forced in OWASP_AREAS:
        status = forced if forced else ("CHECKED" if dep_checked else "NOT_CHECKED")
        count = sum(1 for f in results["findings"] if f["owasp"] == code)
        lines.append(f"| {code} {label} | {status} | {count} |")
    lines += ["", "---", "", "## 4. Findings", ""]
    if not results["findings"]:
        lines.append("No findings requiring attention.")
    for f in results["findings"]:
        lines += [
            f"### {f['id']} — {f['evidence']}", "",
            "| Field | Value |", "|---|---|",
            f"| Severity | `{f['severity']}` |",
            f"| Confidence | `{f['confidence']}` |",
            f"| OWASP | `{f['owasp']}` |",
            f"| Status | `{f['status']}` |",
            f"| File | `{f['file']}` |",
            f"| Line | `{f['line']}` |", "",
            "**Evidence**", "", f"`{f['evidence']}`", "",
            "**Impact**", "", f"`{f['impact']}`", "",
            "**Recommendation**", "", f"`{f['recommendation']}`", "", "---", "",
        ]
    lines += ["## 5. Skipped Checks", "", "| Check | Reason |", "|---|---|"]
    for sk in results["skipped"]:
        lines.append(f"| {sk['check']} | {sk['reason']} |")
    if not results["skipped"]:
        lines.append("| — | none |")
    lines += ["", "---", "", "## 6. Security Gate", "", "```",
              f"Result: {results['status']}", "```", "", "**Reason**", "",
              f"`{results['gate_reason']}`", "", "---", "", "## 7. Recommended Actions", ""]
    if results["findings"]:
        for f in results["findings"]:
            lines.append(f"1. `{f['id']}` — {f['recommendation']}")
    else:
        lines.append("None.")
    lines += ["", "---", "", "## 8. Audit Limitations", ""]
    if results["limitations"]:
        for lim in results["limitations"]:
            lines.append(f"- {lim}")
    else:
        lines.append("None identified.")
    return "\n".join(lines) + "\n"


def main():
    banner()
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--path", default=None, help="Scope to audit (default: repo root)")
    parser.add_argument("--out", default=None, help="Write findings JSON to this path")
    parser.add_argument("--report", default=None, help="Write rendered Markdown report here")
    args = parser.parse_args()

    root = os.path.abspath(args.path) if args.path else (repo_root() or os.getcwd())
    if not os.path.isdir(root):
        die(f"scope path does not exist: {root}")

    counter = {"n": 0}
    findings = []
    checks = []
    skipped = []
    limitations = []

    sec_findings, sec_check = check_secrets(root, counter)
    findings += sec_findings
    checks.append(sec_check)

    cfg_findings, cfg_check, cfg_reason = check_security_configuration(root, counter)
    findings += cfg_findings
    checks.append(cfg_check)
    if cfg_check["status"] == "SKIPPED":
        skipped.append({"check": cfg_check["name"], "reason": f"SKIPPED — {cfg_reason}"})

    mob_findings, mob_check, mob_reason = check_mobile_configuration(root, counter)
    findings += mob_findings
    checks.append(mob_check)
    if mob_check["status"] == "SKIPPED":
        skipped.append({"check": mob_check["name"], "reason": f"SKIPPED — {mob_reason}"})

    dep_findings, dep_check, dep_reason = check_dependency_audit(root, counter)
    findings += dep_findings
    checks.append(dep_check)
    if dep_check["status"] == "SKIPPED":
        skipped.append({"check": dep_check["name"], "reason": f"SKIPPED — {dep_reason}"})

    depl_findings, depl_check, depl_reason = check_deployment_configuration(root, counter)
    findings += depl_findings
    checks.append(depl_check)
    if depl_check["status"] == "SKIPPED":
        skipped.append({"check": depl_check["name"], "reason": f"SKIPPED — {depl_reason}"})

    if not any(c["status"] != "SKIPPED" for c in checks if c["name"] in
               ("dependency-audit", "mobile-configuration", "security-configuration")):
        limitations.append(
            "No application source under this scope yet — most checks had nothing to scan.")
    limitations.append(
        "SAST (semgrep) is not installed in this environment; A03 Injection is NOT_CHECKED.")

    summary = {k: 0 for k in SEVERITY_ORDER}
    for f in findings:
        summary[f["severity"].lower()] += 1

    status, reason = gate_from_summary(summary)

    results = {
        "audit_id": "SEC-AUDIT-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S"),
        "project": os.path.basename(root),
        "date": datetime.date.today().isoformat(),
        "mode": "READ-ONLY",
        "status": status,
        "gate_reason": reason,
        "summary": summary,
        "checks": checks,
        "findings": findings,
        "skipped": skipped,
        "limitations": limitations,
    }

    output_json = json.dumps(results, indent=2)
    print(output_json)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output_json + "\n")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(render_markdown(results))

    sys.exit(1 if status == "BLOCK" else 0)


if __name__ == "__main__":
    main()
