# Threat model

What we protect, the threats we expect and how each is handled. Update it in the same
PR as any change that affects these. StrumBook is a local tool with no credentials of its
own; its only network use is `git` fetching a book file's sources. The development
setup is the main concern.

## Assets

| Asset | Why it matters |
|-------|----------------|
| Private song collections | Other groups' and bands' material; must never become public through this repository |
| The `main` branch | Others may install and build on it |
| Sam's GitHub account and token | Controls all his repositories |

## Trust boundaries

1. **Developer account ↔ personal data.** Development happens in a separate computer
   account holding only public work.
2. **Sandbox ↔ the rest of the account.** Shell commands Claude runs are limited by
   Claude Code's sandbox (`.claude/settings.json`).
3. **Branch ↔ `main`.** Changes reach `main` only by a PR with passing CI, merged by Sam.

## Threats

| Threat | Mitigations | Residual risk |
|--------|-------------|---------------|
| An agent reaches personal data | Separate developer account; sandbox | None while the account holds no personal data |
| Prompt injection from a web page, issue or song file | Sandbox; `CLAUDE.md` treats such text as data; Sam reviews every PR | A bad change could reach a PR; review is the backstop |
| Credential theft | Sandbox and permission rules block reads of credential files and the Keychain; only `git push` and `gh` run outside the sandbox | Credentials stored elsewhere in the developer account |
| Secret committed by mistake | No secrets in this project; GitHub secret scanning and push protection are on | A secret GitHub doesn't recognise is public once pushed |
| Private songs leak into this repository | Collections stay in their own repositories; tests use public-domain songs; CI's sample book (downloadable by anyone signed in to GitHub) builds only `tests/fixtures/`; PR checklist and reviewer check | Human error in a PR; review is the backstop |
| Malicious or mistyped dependency | Sam approves each one; all pinned in `uv.lock`; Dependabot. Runtime: only `typst` (exact pin, as it's pre-1.0); `pypdf` is for tests only | A compromised release of an approved package; `typst` bundles a native compiler we can't easily inspect |
| A fetched collection carries bad content | `make christmas` builds `books/christmas.book.toml`, which clones only pathawks/Christmas-Songs, pinned to a full commit SHA, into the user cache outside the repository; StrumBook reads it as song data and nothing from it is committed; CI doesn't run it | Its songs are untrusted text, covered by the prompt-injection and renderer rows; if the upstream repository disappears, only that target breaks |
| A book file makes `git` do something else (option injection such as `--upload-pack`, `ext::` or `file://` transports, a pin read as an option) | Only `https://` and ssh (`ssh://`, `user@host:path`) addresses are accepted, with no part starting with `-`, and checked before `git` runs; the address follows `--`; pins must look like a commit or tag; a book file can't pass `git` options or config | A bug in `git` itself; a book file can still name any https or ssh host, so building someone else's book file fetches from wherever it says, with the book maker's git sign-in |
| A cached clone is tampered with or goes stale | The cache holds only clones StrumBook made; each build fetches the latest or checks out the pin with `--force`, discarding local edits; offline builds warn that the copy may be out of date; deleting the cache is always safe | Anything that can already write to the user's cache folder |
| A song file abuses the renderer (Typst code injection, reading other files, network) | Song text reaches Typst only as JSON data, never as markup; Typst's root is the bundled `layout/` folder, so it can't read files outside it; no Typst packages, so it never fetches anything | A bug in Typst's own sandbox |
| A bundled font file is tampered with or mislicensed | Atkinson Hyperlegible 1.006 is committed with its OFL licence and SHA-256 hashes (`layout/fonts/README.md`), so a changed file shows in review | A binary diff shows only that a font changed; it can be checked only against the recorded hashes |
| Compromised GitHub Action | Actions (checkout, setup-uv, upload-artifact) pinned to commit SHAs; read-only workflow token | A compromised action at the pinned commit |
| Unreviewed change reaches `main` | Ruleset requires a PR and passing `checks`, blocks force-push and deletion; agents can't merge | Anyone with write access can merge; accepted while Sam is the only one |

## Known limitations

- The sandbox covers shell commands only. Claude's file tools are governed by
  permission rules, which are guardrails rather than a boundary.
- Shell commands can read files elsewhere in the developer account. Acceptable while it
  holds only public work; revisit if that changes.
- Permission rules match command prefixes, so a command written another way can slip
  past them. The sandbox and the `main` ruleset are the real backstops.
