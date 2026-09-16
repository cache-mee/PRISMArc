# Stack

This folder holds the approved technology stack and the coding rules that govern
all code written in this project.

## Files

| File | Owner | Purpose |
|---|---|---|
| `stack-proposal.md` | Architect agent | The full stack proposal, created in Phase 3 of the SDLC workflow. Marked `status: approved` once the user approves it. |
| `rules/base-rules.md` | Architect agent | Coding rules derived from the approved stack. Generated on stack approval. **Do not edit without Architect sign-off.** |
| `rules/client-rules.md` | You | Your client, organisation, and personal rules. Agents read this but never overwrite it. Add anything here. |

## How agents use these files

Every agent in the salon-app SDLC workflow reads `rules/base-rules.md` and
`rules/client-rules.md` as persistent facts before doing any work. Client rules
layer on top of base rules — they do not replace them. Where a client rule
conflicts with a base rule, the client rule wins and the override must be
documented in `client-rules.md`.

## When are these created?

`stack-proposal.md` and `rules/base-rules.md` are generated automatically by the
Architect agent during Phase 3 of `/salon-sdlc-workflow`. `rules/client-rules.md`
is seeded with a starter template at the same time — you fill it in before or
during the Build phase.
