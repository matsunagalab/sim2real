# AUTHOR_GUIDELINES

## Target Journal

- Journal: Computational and Structural Biotechnology Journal (CSBJ)
- Publisher/platform: Science Partner Journal program, distributed by AAAS
- Journal section for this manuscript: General
- Manuscript category: Research Article
- Submission system: Editorial Manager, `www.editorialmanager.com/csbj`
- Official sources checked:
  - CSBJ Guidelines for Authors: `https://spj.science.org/page/csbj/for-authors`
  - CSBJ journal page: `https://spj.science.org/journal/csbj`
  - CSBJ About page: `https://spj.science.org/page/csbj/about`
- Last checked: 2026-06-01.

## Submission Strategy

- Use the CSBJ General section.
- Submit as a Research Article.
- Keep the manuscript compact: 4 main multi-panel figures, no unnecessary tables, and a focused main text.
- Do not submit as a Short Communication unless a full Research Article is rejected for scope or length. CSBJ allows Short Communications up to 10 printed pages or 6,250 words, but the present paper needs enough Methods and Supplementary Materials to document model selection, controls, and reproducibility.
- Do not submit as a Software/Web Server Article. The paper's main claim is a scientific result about simulation-informed learning, not a reusable software resource.
- Do not submit as a Method Article unless the manuscript is rewritten around a generally applicable method as the primary contribution.

## Fit To CSBJ

This manuscript should be framed for the CSBJ General section: computational, structural, and data-driven approaches that improve mechanistic understanding of molecular systems. The strongest fit is a Research Article on simulation-informed transfer learning for protein thermal stability prediction, with emphasis on:

- integration of experimental thermal stability measurements with simulation-derived stability-change information;
- rigorous validation under a target-task-centered model-selection protocol;
- implications for protein engineering workflows and future closed-loop design.

Avoid positioning the work as a pure software/tool paper unless the manuscript is reorganized around reusable software, documentation, and external user reproducibility.

## Section Order

### Single Source Of Truth

`AUTHOR_GUIDELINES.md` is the single source of truth for section order.

### Current Section Order

Use file-name tokens that map to `tex/sections/<token>.tex`.

SECTION_ORDER: abstract -> introduction -> methods -> results -> discussion -> acknowledgments

### CSBJ Mapping

- Title/authors/affiliations are handled in `tex/main.tex`, not in `SECTION_ORDER`.
- `abstract` maps to the manuscript abstract.
- `introduction` maps to Introduction.
- `methods` maps to Materials and Methods, including any theory/calculation content needed for transfer learning, simulation features, model selection, and statistical evaluation.
- `results` maps to Results.
- `discussion` should include the main interpretation and, if needed, a short concluding paragraph. Add a separate `conclusions` section only if the final manuscript needs it.
- `acknowledgments` should include funding, author contributions if not handled elsewhere, competing interests, data/code availability, and any required AI-use disclosure.
- References are handled after the main sections in `tex/main.tex`.
- `supplementary` is handled after references in `tex/main.tex` and is not part of `SECTION_ORDER`.

If `SECTION_ORDER` changes, sync `tex/main.tex` and `OUTLINE.md`.

## Article Limits

For CSBJ Research Articles, there is no hard length limit, but the editors recommend:

- Main text length: no more than about 25 printed pages or 15,000 words in most cases.
- Display items: no more than 10 figures and 5 tables in most cases.
- Supplementary material: keep to supporting details that are not essential for understanding the main argument.

Working target for this paper:

- Main figures: 4.
- Main tables: 0 to 2, only if needed.
- Main text length: aim for about 5,000 to 8,000 words, excluding references, figure legends, and supplementary material.
- Supplementary figures/tables: model details, additional controls, replicate-level metrics, and sensitivity analyses.

## Required Manuscript Components

Prepare the submission package with:

- Cover letter.
- Title page information: title, authors, affiliations, corresponding author, and ORCID IDs where available.
- Abstract.
- Main manuscript text.
- References.
- Figure legends and table legends.
- Figures and tables cited consecutively in the text.
- Supplementary Materials, if used.
- Data availability statement.
- Code availability statement.
- Funding statement.
- Competing interests or conflict of interest statement.
- Author contributions, preferably in CRediT style unless the template requires another format.
- AI-use disclosure in the cover letter and acknowledgments if AI-assisted tools were used in writing, presentation, analysis, or figure preparation.
- Suggested reviewers, if the submission system requests them.
- Related manuscripts under consideration or in press, if any.

The cover letter should include:

- manuscript title and a brief summary of the main point;
- a statement that none of the material has been published or is under consideration elsewhere, including online;
- confirmation that all listed authors have reviewed and agree to the journal's Publication Ethics policies;
- names, email addresses, and ORCID IDs for all authors;
- identification of the corresponding author.

The submission system may also request:

- names, affiliations, and email addresses of potential referees;
- copies of related papers by the authors that are in press or under consideration elsewhere.

Publication forms are required before acceptance, not necessarily at initial submission:

- License to Publish form for each author.
- Conflict of Interest form for each author.
- Third-party image or asset permissions, if reused material is included.

During submission, the submitting author must confirm compliance with policies on:

- authorship;
- prior publication;
- informed consent;
- animal care and use;
- related papers;
- citations to personal communications and unpublished data;
- data deposition and availability;
- license selection;
- materials sharing;
- third-party image reuse;
- publication of the accepted version.

## Submission Format

- Use the CSBJ Word or LaTeX manuscript template when preparing the final submission.
- Preferred submission format is Microsoft Word `.docx`; `.doc` or LaTeX format is also allowed.
- Initial submission may be a single manuscript file containing text, references, figures, legends, tables, and supplementary material.
- If using LaTeX, a PDF manuscript is acceptable for review, but source files should be kept ready.
- Separate figure files should be available for revision/final production.
- Use zipped files for unusually large supplementary files.
- If a manuscript is on bioRxiv, direct transfer into the submission system is available.

For a Research Article, the body text must include:

- Title.
- Authors and affiliations.
- Abstract.
- Introduction.
- Materials and Methods.
- Results.
- Discussion.
- Acknowledgments.
- References.
- Figures and Tables.
- Supplementary Materials, if used.

## Experimental Design And Statistics

CSBJ encourages clear reporting of study design and statistical analysis.

- In the first part of Materials and Methods, consider using the subtitle `Experimental and Technical Design`.
- Include a diagram or flowchart showing materials, treatments, measurements, data collection, and analysis workflow when it helps reviewers follow the study.
- Describe statistical methods with enough detail for a knowledgeable reader with access to the data to verify the results.
- Follow relevant discipline-specific reporting guidelines when applicable.

For this manuscript, the Methods should explicitly report:

- data sources and inclusion/exclusion criteria;
- train/validation/test split construction;
- target-task validation used for model selection;
- random seeds and replicate handling;
- confidence interval estimation;
- statistical comparison of paired model predictions;
- software versions and hardware where relevant.

## Figure Rules

CSBJ's figure guidance is directly relevant to this manuscript. Apply the following rules to all publication figures:

- Do not put figure titles inside figure panels. Put the title/summary in the figure legend.
- Keep panel labels minimal and consistent. CSBJ prefers lower-case labels in parentheses, e.g. `(a)`, `(b)`, `(c)`.
- Cite figures in consecutive order in the manuscript.
- Keep panels close together and avoid repeating common axis labels unnecessarily.
- Avoid wasted white space, clutter, grid lines, and minor tick marks.
- Do not extend axes beyond the plotted data range unless scientifically necessary.
- Use simple legends/keys; put details in the caption.
- Use solid symbols where possible.
- Ensure symbols remain legible after reduction; minimum symbol size about 6 pt.
- Ensure line widths remain legible after reduction; minimum line width about 0.5 pt.
- Avoid red/green pairings and avoid colors that are too close in hue.
- Avoid grayscale-only encodings.
- Prefer vector output for plots and diagrams. Keep high-resolution source files for revision.
- Bitmap figures should be at least 300 dpi unless a lower resolution is scientifically justified.
- Acceptable figure formats include PDF, PS, EPS, TIFF, JPEG, PNG, PSD, and related production formats.
- For revision/final production, each figure or image should be in a separate editable file format.
- Do not rely on PowerPoint or Word figures for final production.

## Graph Labels And Numbers

- Use clear axis labels with variable name and units in parentheses where applicable.
- Use SI notation where applicable.
- Use powers of 10 for very large or small scales rather than programming-style exponential notation.
- Use leading zeros for decimals, e.g. `0.3`, not `.3`.
- Report only meaningful significant digits.
- Capitalize labels sentence-style, not title-style, unless proper nouns require capitalization.
- Variables should be italicized in the manuscript and figure labels where typographically possible.
- Vectors should be roman boldface if needed.

## Tables

- Cite tables consecutively in the manuscript.
- Give every table a descriptive title.
- Include units in column headings when numerical measurements are shown.
- Do not use vertical rules.
- Keep large secondary tables in Supplementary Materials.

## Citation Style

- References may be submitted in any style initially.
- If accepted, CSBJ reformats references in Chicago style.
- References must be complete and accurate.
- Number references consecutively in order of first citation.
- Cite references in the text using numbers in square brackets, e.g. `[9]` or `[9, 10]`.
- Every reference in the list must be cited in the text; uncited references may be removed.
- Include DOIs where available.
- List all authors by first initial(s) and last name; do not replace the full author list with `et al.` in the reference list.
- Do not use `op. cit.`, `ibid.`, 3-em dashes, or en dashes as substitutes in references.
- For journals without page ranges, use the article number.
- Posted preprints can be included with appropriate identification and a persistent identifier such as a DOI.

## Supplementary Materials

Use Supplementary Materials for:

- run-level metrics and confidence intervals;
- hyperparameter search details;
- dataset splits and leakage checks;
- model-size and encoder-freezing controls;
- additional negative controls;
- extended implementation details needed for reproducibility.

Supplementary text, figures, and tables can be included at the end of the main manuscript file if manageable, or uploaded separately.

## Data And Code

CSBJ encourages transparent research-data handling. For this manuscript:

- Provide processed data tables needed to reproduce the figures.
- Provide scripts or notebooks used to generate figures.
- State whether raw simulation trajectories are available, too large to deposit, or available on request.
- If possible, deposit a snapshot of code and processed data in a stable archive with a DOI.
- Ensure the manuscript reports train/validation/test splitting, model-selection criteria, confidence intervals, and random seeds clearly enough for review.

## AI Policy

AI-assisted technologies cannot be listed as authors. If AI tools were used for writing, presentation, coding assistance, analysis support, or figure preparation, disclose this in:

- the cover letter; and
- the acknowledgments or other disclosure section required by the template.

Do not cite AI tools as scholarly sources.

## Open Access And Licensing

CSBJ is open access and publishes under a Creative Commons Attribution license. Authors retain copyright and grant the publication license required by the journal.

## Immediate To-Do For This Manuscript

- Convert the current paper template toward the CSBJ template.
- Check that all main figures have no in-panel titles.
- Consider changing panel labels to `(a)`, `(b)`, `(c)` style before submission.
- Add required statements: data availability, code availability, competing interests, funding, author contributions, and AI-use disclosure.
- Prepare a concise cover letter emphasizing why simulation-derived stability-change information improves thermal-stability prediction.
- Verify that figures and legends can stand alone without local project terminology.
- Prepare a clean supplementary package with run-level metrics and reproducibility details.
