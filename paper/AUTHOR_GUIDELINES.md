# AUTHOR_GUIDELINES

## Target Journal

- Journal: **Biophysics and Physicobiology (BPPB)**
- Publisher: **The Biophysical Society of Japan**
- Online ISSN: 2189-4779 (open access, J-STAGE)
- Manuscript category: **Regular Article**
- Submission system: ScholarOne Manuscripts, `https://mc.manuscriptcentral.com/biophysics`
- Official sources checked:
  - Journal page: `https://www.biophys.jp/biophysics_and_physicobiology.html`
  - Instructions for Authors: `https://www.biophys.jp/biophysics_and_physicobiology03.html`
  - Quick Guide: `https://www.biophys.jp/biophysics_and_physicobiology_quickguide.html`
- Last checked: 2026-07-13.
- NOTE: Rules below are transcribed from the official Instructions for Authors. Do NOT invent
  rules; if a detail is not covered here, re-check the source before asserting it.

## Article Types (BPPB)

Regular Article, Review Article, Note, Method and Protocol, Database and Computer Program,
Commentary and Perspective, Editorial. **This manuscript = Regular Article.**

## Section Order

### Single Source Of Truth

`AUTHOR_GUIDELINES.md` is the single source of truth for section order. If `SECTION_ORDER` changes,
sync `tex/main.tex` (the `\input{sections/...}` block) and `OUTLINE.md` headings (see `paper/CLAUDE.md`).

### BPPB required order (Regular Article)

Official required sequence:

> Introduction, Materials and methods (or Methods), Results, Discussion (or Results and discussion),
> Conclusion, Conflict of interest, Author contributions, Data availability, Acknowledgements, References.

(An optional preprint notation may appear before Acknowledgements.)

### SECTION_ORDER (file-name tokens → tex/sections/<token>.tex)

SECTION_ORDER: introduction -> methods -> results -> conclusion

Front matter (handled in `tex/main.tex`, not in SECTION_ORDER): title, authors, affiliations,
**abstract**, **Significance statement (<100 words)**, and **keywords (≤5)**. The graphical
abstract and its caption are separate submission files.

Back matter after `conclusion` (in `tex/main.tex`, after the SECTION_ORDER block, before References):
**declarations** = Conflict of interest → Author contributions → Data availability → Acknowledgements.
Supplementary Materials are compiled as a separate PDF from `tex/supplementary_main.tex`; they
are not appended to the main manuscript and are not part of SECTION_ORDER.

### Mapping

- `introduction` → Introduction.
- `methods` → Materials and Methods (data, transfer-learning model, simulation labels, model
  selection, statistics; third-party-reproducible detail).
- `results` → Results and discussion (results tied to figures, followed by interpretation,
  comparison to prior work, and limitations in the same section).
- `conclusion` → **Conclusion (separate section, required by BPPB).** A compact closing (not a
  summary rehash): the main advance and its take-home significance.
- `declarations` → Conflict of interest, Author contributions (CRediT-style), Data availability,
  Acknowledgements — in BPPB order.

## Abstract

- **≤ 250 words**, single paragraph.
- **Must NOT include references.**
- Structure: background (1) → problem (1) → approach (1) → key result with numbers (1–2) → significance (1).

## Significance Statement

- **Required. Less than 100 words.** A plain-language statement of why the paper matters.
- Placed in front matter (after abstract/keywords, per template).

## Keywords

- **Up to five** keywords.

## Graphical Abstract

- **Mandatory for Regular Articles.** One figure (color or monochrome) depicting the manuscript content.
- Caption **< 100 words**.
- 300 dpi; TIFF, PNG, or JPEG.

## References / Citation Style

- **Numbered**, sequentially in order of first appearance in the text.
- In-text citation as bracketed numbers, ranges collapsed: **`[1,3,5-8]`**, placed *before* punctuation.
- Every listed reference must be cited; list must be complete and accurate (include DOIs where available).
- Do NOT fabricate BibTeX (see `paper/CLAUDE.md`). bibkey format `FirstAuthorYYYYShortTitle`.
- Implementation: the current LaTeX uses `\bibliography{refs}` — ensure a **numeric** bibliography
  style (e.g. `unsrt`/journal .bst), not author–year, so citations render as `[n]`.

## Figures and Tables

- **300 dpi minimum**; figure formats TIFF, PNG, or JPEG (vector PDF kept as source for production).
- Tables and figures should be embeddable in the template file; cite consecutively.
- Panel labels: keep minimal; no in-panel figure titles (put the title/summary in the legend).
- Avoid red/green pairings, grayscale-only encoding, clutter, and gridlines where avoidable.
- Use leading zeros (`0.3` not `.3`), report only meaningful significant digits, units in axis labels.

## Length

- The Instructions specify **no maximum word or page count** for Regular Articles.
- Working target for this paper: 4 main figures + 1 graphical abstract; compact main text
  (~5,000–8,000 words excluding references/legends/supplementary); reproducibility detail in
  Supplementary Materials.

## Declarations (required sections, BPPB order)

- **Conflict of interest** — declare or state none.
- **Author contributions** — CRediT-style.
- **Data availability** — where processed data / code / trajectories are (Zenodo DOI placeholder;
  raw MD/FEP too large → deposited/available as noted).
- **Acknowledgements** — funding and thanks.

## AI Policy

AI-assisted tools cannot be authors. BPPB does not require a formal declaration when an LLM is used
only to search prior studies or revise English grammar. A substantial contribution to manuscript
development requires the tool name, version, and a reproducible description in Acknowledgements.
AI-generated article figures are prohibited.

## Open Access / License

BPPB is open access on J-STAGE (Creative Commons). Confirm the license selection at submission.

## BPPB conversion status

- [x] Add a **Conclusion** section (`tex/sections/conclusion.tex`) and wire it into the manuscript.
- [x] Add **Significance statement (<100 words)** and **keywords (≤5)** to front matter.
- [x] Create the **graphical abstract** (300 dpi) and a separate caption (<100 words).
- [x] Add **Conflict of interest / Author contributions / Data availability / Acknowledgements** in
      BPPB order (`tex/sections/acknowledgments.tex`).
- [x] Use the official numeric `bppb.bst` bibliography style.
- [x] Replace the former HenriquesLab class with the official **BPPB LaTeX template** dated
      8 May 2025 (`bppb.cls`, `bppb.bst`, and `bppb-logo.pdf`).
- [x] Compile Supplementary Materials as a separate PDF.
- [ ] Cover letter reframed for BPPB (biophysics framing; no prior/dual submission; author ORCIDs).
