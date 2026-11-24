# CR-0002: Problem statement and project direction

| Field         | Value                                                    |
|---------------|----------------------------------------------------------|
| Status        | Approved                                                 |
| Author        | sam-tmts (drafted with Claude)                           |
| Created       | 2026-11-24                                               |
| Semver impact | none: documentation only                                 |

## Why

The problem, the direction and the findings so far live in a claude.ai Project, not in
the repository, so Claude Code sessions and anyone browsing the repository can't see
them. Putting a general version in the repository gives every session the same starting
point and lets future CRs refer to it.

The repository is public, so it must contain nothing about any group's private song
collection.

## Scope

**In:**

- `docs/problem-statement.md`: the problem; the direction (songs as ChordPro files in
  each group's own repository; an importer with a human check; books built from one or
  more collections; what every book must have); what's parked; the ground rules (open
  source tool, private song collections, public repository holds only public-domain test
  songs); the standard layout of a song collection repository; books drawn from several
  collections; and what was learnt from trying ChordPro as the renderer.
- `CLAUDE.md`: fill in the **Project** line, and add a project note pointing to
  `docs/problem-statement.md`, so every session reads it.

**Out:**

- The rest of the first-CR housekeeping (README, changelog reset, tooling, CI jobs,
  architecture, threat model, test plan). That comes with the first code CR, once the
  language and tooling are chosen.
- Anything specific to a private collection (song names, survey data, group or band
  details). That stays in each collection's own repository.

## Design notes

One document rather than several: the material is short and read as a whole. It is a
statement of intent, not a specification; each later CR turns a part of it into
acceptance criteria. Decisions that later work must respect (for example, ChordPro as
the renderer) get their own ADRs when a CR depends on them, not in this CR.

## Acceptance criteria

- [ ] AC1: `docs/problem-statement.md` covers every item listed under **In**.
  *Verified by:* manual check by the owner in review.
- [ ] AC2: Nothing in the pull request names a private collection, a group or band, a
  person other than the owner, or any song other than public-domain examples.
  *Verified by:* manual check by the owner in review.
- [ ] AC3: `CLAUDE.md` names the project and points to the problem statement.
  *Verified by:* manual check by the owner in review.
- [ ] AC4: The `Markdown lint` CI check passes. *Verified by:* CI.

## Constraints and risks

Public repository: the main risk is leaking private details from the claude.ai Project
notes, which AC2 guards against. No code, dependencies or protected paths change.

## Approval log

| Gate | Date | By | Notes |
|------|------|----|-------|
| CR approved | 2026-11-24 | sam-tmts | In chat |
| Plan approved | 2026-11-24 | sam-tmts | In chat |
| PR merged | | | |
| Released | | | |
