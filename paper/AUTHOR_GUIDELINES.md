# JOURNAL_RULES

## Target Journal
This repository is journal-agnostic. Fill this in only when a specific submission target is chosen for a draft.
If no journal is chosen, keep this section as-is and use the default section order below.

## Section Order
### Single source of truth
`AUTHOR_GUIDELINES.md` is the **single source of truth** for section order.

### Format
- Use **file-name tokens** that map to `tex/sections/<token>.tex`
- Use `->` to separate tokens
- This order is allowed to change depending on the submission rules (e.g., Methods at the end)

### Current section order (tokens)
SECTION_ORDER: abstract -> introduction -> methods -> results -> discussion -> acknowledgments

### Journal-agnostic policy
- If the target journal is unknown, keep the default `SECTION_ORDER` above.
- If a journal requires a different order, update `SECTION_ORDER` and then sync `tex/main.tex` and `OUTLINE.md`.

### Notes
- `supplementary` is handled **after** references in `tex/main.tex` and is not part of `SECTION_ORDER`.

## Word/Figure Limits
- Word limit: Not set (journal-specific)
- Figure limit: Not set (journal-specific)
- Table limit: Not set (journal-specific)

## Required Sections
Not fixed. Update only when a target journal is selected.

## Submission Items
Not fixed. Update only when a target journal is selected.
