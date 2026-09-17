# Security Audit Report

## 1. Audit Summary

| Field | Value |
|---|---|
| Project | `<project-name>` |
| Audit ID | `<SEC-AUDIT-ID>` |
| Date | `<YYYY-MM-DD>` |
| Auditor | `Security Agent` |
| Mode | `READ-ONLY` |
| Result | `PASS / WARN / BLOCK` |

### Findings

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Informational | 0 |

---

## 2. Checks Performed

| Check | Status | Tool |
|---|---|---|
| Dependency vulnerabilities | PASS / WARN / FAIL / SKIPPED | `<tool>` |
| Secrets | PASS / WARN / FAIL / SKIPPED | `<tool>` |
| Security configuration | PASS / WARN / FAIL / SKIPPED | `<tool>` |
| Mobile/Expo configuration | PASS / WARN / FAIL / SKIPPED | `<tool>` |
| Deployment configuration (Dockerfile/nginx) | PASS / WARN / FAIL / SKIPPED | `<tool>` |

Only checks actually attempted are listed.

---

## 3. OWASP Coverage

| OWASP Area | Status | Findings |
|---|---|---:|
| A01 Broken Access Control | CHECKED / NOT_CHECKED / N/A | 0 |
| A02 Cryptographic Failures | CHECKED / NOT_CHECKED / N/A | 0 |
| A03 Injection | CHECKED / NOT_CHECKED / N/A | 0 |
| A04 Insecure Design | CHECKED / NOT_CHECKED / N/A | 0 |
| A05 Security Misconfiguration | CHECKED / NOT_CHECKED / N/A | 0 |
| A06 Vulnerable Components | CHECKED / NOT_CHECKED / N/A | 0 |
| A07 Authentication Failures | CHECKED / NOT_CHECKED / N/A | 0 |
| A08 Software/Data Integrity | CHECKED / NOT_CHECKED / N/A | 0 |
| A09 Logging/Monitoring | CHECKED / NOT_CHECKED / N/A | 0 |
| A10 SSRF | CHECKED / NOT_CHECKED / N/A | 0 |
| M-NET Mobile Insecure Communication | CHECKED / NOT_CHECKED / N/A | 0 |

A category is `CHECKED` only if a check for it actually ran. `NOT_CHECKED`
means no applicable check exists yet — never claim coverage that wasn't run.

---

## 4. Findings

Only findings that require attention are listed.

### SEC-001 — `<short finding title>`

| Field | Value |
|---|---|
| Severity | `CRITICAL / HIGH / MEDIUM / LOW / INFO` |
| Confidence | `HIGH / MEDIUM / LOW` |
| OWASP | `<category>` |
| Status | `OPEN / FALSE_POSITIVE / ACCEPTED / RESOLVED` |
| File | `<path>` |
| Line | `<line>` |

**Evidence**

`<concise, redacted evidence>`

**Impact**

`<concise impact>`

**Recommendation**

`<concise actionable recommendation>`

---

## 5. Skipped Checks

| Check | Reason |
|---|---|
| `<check>` | `<reason>` |

Skipped is never treated as passed.

---

## 6. Security Gate

```
Result: PASS / WARN / BLOCK
```

**Reason**

`<one concise sentence>`

---

## 7. Recommended Actions

1. `<SEC-001> — action`

---

## 8. Audit Limitations

`<meaningful limitations, e.g. scanners unavailable, no application code present yet>`

If none: `None identified.`
