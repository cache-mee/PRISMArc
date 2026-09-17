# Project Config

Machine-readable project configuration, parsed by `tools/_lib/config_parse.py`.
Rows are `| Label | Value |`; see that file's docstring for the exact lookup
functions and format each one expects. Human-facing rules stay in `CLAUDE.md`
and `stack/rules/` — this file exists only so scripts under `tools/` have one
place to read the same declared values from, instead of hardcoding them.

## Repository Layout

Mirrors `CLAUDE.md` → "Repository layout". Consumed by
`tools/scope-check/scope-check.py`. If this table ever changes, update it here
*and* in `CLAUDE.md` — this file is the value scripts read; `CLAUDE.md` is the
human-facing rule that explains why.

| Setting | Value |
|---|---|
| Backend folder | B2B_BE/ |
| Frontend folder | B2B_FE/ |
