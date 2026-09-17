# OWASP Checks Reference

Kept deliberately small: only what this repository's checks can realistically
detect, and the mapping from check → OWASP category. Not a general OWASP
knowledge base — for full category rationale, see owasp.org.

## OWASP Top 10 (2021) — coverage from this skill's checks

| Area | Detected by | Realistic here? |
|---|---|---|
| A01 Broken Access Control | — | Not automatable from static checks; requires manual/architectural review |
| A02 Cryptographic Failures | secrets scan, weak-hash scan, insecure-URL scan | Yes |
| A03 Injection | SAST (semgrep), if installed | Only if semgrep available; otherwise NOT_CHECKED |
| A04 Insecure Design | — | Not automatable |
| A05 Security Misconfiguration | CORS-wildcard scan, debug-flag scan, insecure-URL scan | Yes |
| A06 Vulnerable/Outdated Components | dependency audit (`npm audit` / `pnpm audit`, or `pip-audit`) | Yes, when a manifest/lockfile exists and the tool is installed |
| A07 Identification/Auth Failures | — | Not automatable from static checks |
| A08 Software/Data Integrity Failures | — | Not automatable here |
| A09 Logging/Monitoring Failures | dangerous-logging heuristic (secret-like values passed to log/print) | Partial, heuristic only |
| A10 SSRF | — | Requires data-flow analysis; out of scope for static checks |

## Mobile (React Native / Expo) — applicable subset

| Area | Detected by | Realistic here? |
|---|---|---|
| M-NET Insecure Communication | `app.json`/`app.config.js` cleartext-traffic / ATS-arbitrary-loads check | Yes, when an Expo/RN config file exists |
| M-STORAGE Insecure Data Storage | — | Would require app-runtime inspection; out of scope for static checks |
| M-SECRETS Hardcoded secrets in native config | secrets scan (applies repo-wide, including native config files) | Yes |

## Check → OWASP mapping (as emitted by the tool)

| Check id | OWASP tag | Notes |
|---|---|---|
| `secrets` | A02 | Credential/key patterns; severity varies by pattern confidence |
| `insecure-url` | A02 | Plaintext `http://` to a non-local host |
| `weak-crypto` | A02 | `md5`/`sha1` used where a cryptographic hash is implied |
| `cors-wildcard` | A05 | `Access-Control-Allow-Origin: *` or equivalent |
| `debug-flag` | A05 | Debug/verbose flags left enabled in config |
| `dangerous-logging` | A09 | Secret-like variable name passed to a log/print call |
| `dependency-audit` | A06 | Severity taken directly from the scanner's own rating (`npm`/`pnpm audit`, or `pip-audit` for Python manifests) |
| `mobile-cleartext` | A05 | `usesCleartextTraffic` / `NSAllowsArbitraryLoads` true |
| `env-secret` | A02 | Unquoted `.env`-style `KEY=VALUE` where KEY looks like a credential and VALUE isn't a known placeholder |
| `connection-string-credentials` | A02 | `scheme://user:password@host` style URL with a non-placeholder password segment |
| `deployment-configuration` | A05 | Dockerfile with no `USER` instruction (runs as root), or nginx.conf missing all common security headers |

## Status values

- `CHECKED` — a check for this area ran in this audit (found something or not).
- `NOT_CHECKED` — no check for this area exists yet, or its scanner was
  unavailable. Never reported as passed.
- `N/A` — not applicable to this repository (e.g. no mobile config present).

## Severity vs. confidence

- **Severity** = potential impact if the finding is real (CRITICAL/HIGH/MEDIUM/LOW/INFO).
- **Confidence** = strength of the evidence for the finding being real, not a
  false positive (HIGH/MEDIUM/LOW).
- The two are independent: a HIGH-severity finding can carry LOW confidence
  (e.g. a generic secret-pattern match) and must be reported as such, not
  upgraded or downgraded to make the two agree.
