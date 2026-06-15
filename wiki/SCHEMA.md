# Wiki Schema

## Identity
- **Path:** /home/scott/Working/retirement-models/wiki
- **Domain:** Retirement financial model — application architecture, configuration system, and financial simulation models
- **Source types:** Python source files, JSON config files, README, SQL migrations
- **Created:** 2026-06-14

## Page Frontmatter
Every wiki page must start with:
```
---
title: <page title>
tags: [tag1, tag2]
sources: [source-slug1]
updated: YYYY-MM-DD
---
```

## Cross-References
Use `[[slug]]` where slug = filename without `.md`.
Example: `[[simulation-engine]]` → `wiki/pages/simulation-engine.md`

## Citations

Cite every non-common-knowledge factual claim. "Common knowledge" = uncontroversial,
undergraduate-level facts in this wiki's domain. Granularity is paragraph or claim,
never per-sentence. If you cannot produce a citation in one of the forms below,
find one, weaken the claim, or drop it.

Format: Markdown footnotes. Two citation kinds, three valid targets.

**Quote citation** (preferred):
```
The model uses monthly time steps.[^1]

[^1]: raw/README.md §Design/Simulation Loop — "steps monthly from start_date to end_date"
```

**Synthesis citation** (when no single quote captures the claim):
```
Asset state is reset when the period falls outside active dates.[^2]

[^2]: raw/assets.py §period_update [synthesis] — both the pre-start and post-end branches
      call initialize_asset_metrics() or return zeros
```

Three rules for every footnote:

1. **The cited target is one of three forms:**
   - `[[source-slug]]` — a source-type wiki page
   - `raw/<file>` or `assets/<file>` — a path to a local file
   - `<URL>` — a live URL or ephemeral source

2. **A locator is present:** `§<section>`, `p.<n>`, line range, or `(YYYY-MM-DD)`.

3. **Either a verbatim quote, or the `[synthesis]` tag plus a description.**

## Log Entry Format
```
## [YYYY-MM-DD] <operation> | <title>
```
Operations: init, ingest, query, update, lint, audit

## Index Categories
- Architecture
- Models
- Config
- API
- Flows

## Conventions
- raw/ is immutable — skills never modify it
- log.md is append-only — never rewritten, only appended
- index.md is updated on every operation that adds or changes pages
- All pages live flat in wiki/pages/ — no subdirectories
- overview.md reflects the current synthesis across all sources
- README boundary: wiki pages must not duplicate README content. Extract structural signals; link to the README for operational content (setup, contributing, running). When ingesting any README, also evaluate it for gaps and suggest edits.
