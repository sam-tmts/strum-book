# Security

## Reporting a problem

Report ordinary bugs as GitHub issues. For anything sensitive, such as a vulnerability,
leaked credentials or private songs, use GitHub's private vulnerability reporting on
this repository instead of a public issue.

## Risks and how we handle them

StrumBook is a local command-line tool. It handles no credentials and, so far, makes no
network requests. The development setup is sized to that.

| Risk | What we do |
|------|------------|
| A coding agent reaches personal files | Development happens in a separate computer account holding only public work. Claude Code's sandbox (`.claude/settings.json`) limits shell commands to writing inside the project and reaching GitHub and PyPI. Reads of credential files and the Keychain are blocked. |
| Private songs leak into this public repository | Collections stay in their own repositories; tests use public-domain songs only; reviews check for leaks. |
| A malicious or mistyped dependency | Few dependencies, each approved before it's added, all pinned in `uv.lock`. CI actions are pinned by commit and updated by Dependabot. |
| An agent merges or damages `main` | Agents push only task branches and can't merge. `main` is protected on GitHub, and Sam merges. |

**Known limits.** `git push` and `gh` run outside the sandbox because they need the
stored GitHub credentials. Shell commands can still read files elsewhere in the
development account, which is acceptable while that account holds nothing private.
Revisit this if that changes, or when StrumBook gains network or upload features.
