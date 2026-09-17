# .githooks/

Versioned git hooks for this repo. Git does not read hooks from here by
default — `.git/hooks/` is local, untracked, and never populated by `git
clone` — so each clone opts in once:

```sh
git config core.hooksPath .githooks
```

## pre-commit

Runs `tools/scope-check/scope-check --staged` and blocks the commit if the
staged changes touch both `B2B_BE/` and `B2B_FE/` (`CLAUDE.md`'s Repository
layout rule). This is local, fast feedback before you even push.

It is not a substitute for the CI check
(`.github/workflows/scope-check.yml`), which runs on every pull request
regardless of whether this hook is installed — that is the rule's real
backstop. This hook exists to catch a violation earlier, not instead.

## Bypassing (don't, without a reason)

`git commit --no-verify` skips this hook. The CI check still applies and
will fail the PR — bypassing locally only defers the failure.
