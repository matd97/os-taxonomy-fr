# Methodology

How the French Curriculum Taxonomy was built: a complete, verifiable account of the pipeline that turned the official French programmes into 14,549 coded standards, 6,051 micro-topics, a 10,050-edge prerequisite graph, 845 cluster summaries, and an interactive 3D viewer.

The project replicates, for France, the structure of [Marble's os-taxonomy](https://github.com/withmarbleapp/os-taxonomy) (US/UK curricula). It was executed over three days (2026-07-10 to 2026-07-12) by orchestrated fleets of AI agents (~1,700 agent runs, ~140M tokens) with deterministic code enforcing every global constraint. The guiding principle throughout: **agents propose, code disposes**. Judgment calls (extraction, atomization, adjudication) go to language models working in small, verifiable units; global properties (coverage accounting, deduplication bookkeeping, acyclicity, schema validity) are enforced by plain programs that cannot hallucinate.

## Scope decisions (locked before any extraction)

| Decision | Choice |
|---|---|
| Tracks | Voie générale only (PS through Terminale, incl. 13 spécialités and the optional layer). Voie technologique and professionnelle out of scope. |
| Version pin | Rentrée 2025: only texts in force at that date. The 2026-2027 reform wave is catalogued but not extracted, eliminating version conflicts by construction. |
| Language | Standards keep verbatim French (Licence Ouverte permits it); micro-topics carry English names/descriptions plus French names, for cross-mapping with Marble's English graph. |
| Depth | Full clone: standards, then topics, then prerequisite DAG and clusters, as three sequential phases with review between each. |

## Phase 0: Source research (9 → 127 documents)

Nine research agents ran in parallel, one per segment of the system (cycle 1 maternelle, cycles 2-4, seconde, tronc commun 1re-Tle, the 13 spécialités, a system-map agent for the socle commun / attendus / horaires, and an open-data hunt across data.gouv.fr and ScoLOMFR). Each agent's findings were then checked by a verification agent that fetched the claimed URLs and confirmed titles, versions, and in-force status. A completeness critic reviewed the merged inventory the way a French teacher would ("where is DGEMC?") and a gap-fill pass closed what it found, including correcting one of the critic's own citations.

Result: 127 verified documents in `sources.json`, each with URL, direct PDF where available, Bulletin officiel reference, in-force status, and an extractability assessment. Key structural findings: the finest-grained artifacts are the attendus de fin d'année (CP-3e, four subjects); no one, including the ministry, publishes the programme *content* as structured data; and ScoLOMFR/BCN provide the official vocabulary skeleton but not the leaves.

## Phase A: Standards extraction (127 → 91 → 14,549)

**Corpus.** The 127 sources were filtered to 91 content-bearing, in-force, deduplicated documents. Downloading met two bot walls: education.gouv.fr and éduscol serve Datadome/Cloudflare challenges. Two discoveries unlocked the corpus: the block is TLS-fingerprint based (curl passes where python-requests fails), and the annexe PDFs live on unprotected file stores (`/sites/default/files/`, static.data.gouv.fr, académie mirrors). 35 documents downloaded directly; 55 recovery agents each hunted, curl-verified, and downloaded an alternative source for one blocked document (55/55 success, including one Wayback Machine capture and two headless-browser renders). Mapper agents later exposed that two corpus files were BO boilerplate without their annexe (arts and SVT terminale spécialités); the real annexes were fetched and the corpus finalized at 91.

**Extraction.** Each document was charted by a mapper agent into units of one subject and at most ~14 PDF pages (246 units total), using pdftotext for fast scanning and native PDF vision for table boundaries. One extractor agent per unit then copied out every enumerable item verbatim: one standard per attendu bullet, per Contenus/Capacités table row, per connaissance-compétence pair, per socle composante. The instruction set forbade paraphrase, translation, merging, and invention; prose programmes yielded their stated objectives sentence by sentence. Every unit then faced an adversarial verifier that sampled eight standards for verbatim fidelity against the source pages, re-scanned sample pages for missed items, and repaired the JSON in place. Final verdicts: 229 pass, 15 fixed, 0 fail.

**Resilience.** Extraction agents wrote results to disk before reporting, and a generator script diffed charted units against files on disk to emit each next run covering only what was missing. This made the pipeline immune to interruption (it survived seven monthly-spend-cap cutoffs without losing a completed unit) and is the pattern used for every later phase.

**Assembly.** Deterministic code merged the 244 unit files, removed 559 exact duplicates, minted codes, grouped standards into 17 curriculum families (fr-socle-2015, fr-cycle3-frmaths-2025, fr-lycee-specialites-2019, ...), and validated the result against Marble's own `curriculum-standards.schema.json`. Output: **14,549 standards**, each carrying verbatim French text, subject, the document's own domain heading, grade levels, kind (attendu/capacité/connaissance/objectif/repère), page locator, and BO reference.

## Phase B: Atomization and deduplication (14,549 → 6,051 topics)

**Atomization.** The standards were batched into 207 (subject × age-band) groups of ≤90. One agent per batch distilled them into micro-topics in Marble's sense: one teachable idea, with an English name and description, a French name, a type (CONCEPTUAL / PROCEDURAL / REPRESENTATIONAL / LANGUAGE / META), an age range from the source levels, 2-4 observable mastery-evidence bullets, and back-links to every covered standard. Coverage was accounted exactly: every one of the 14,549 keys had to land in a topic or be explicitly discarded with a reason (235 were, as pedagogy notes or exam-organization text). Yield: 6,710 raw topics.

**Deduplication, in three gates.**
1. *Embedding gate*: all raw topics embedded with `gemini-embedding-001`; candidate near-duplicates = cosine ≥ 0.86 within a subject, ≥ 0.90 across subjects (1,952 pairs).
2. *Adjudication*: 89 panels of ~22 pairs each ruled merge vs distinct under an explicit doctrine: same idea reworded (or sourced from a different document family) merges; the same theme at a different depth or age stays distinct, because progression steps are the graph's substance. 690 merges.
3. *Per-subject critics*: 42 agents audited each subject's full topic list for residual duplicates and impossible ages, conservatively (35 more merges, 6 age corrections).

Merges were applied by union-find in code, with survivor selection by adjudicator vote, unions of standards/evidence, and age-range widening. A later whole-dataset audit caught 8 final duplicates and one systematic age bug: 28 topics distilled from CECRL proficiency standards (which have no grade level) carried null ages; they were re-aged using France's official CECRL milestones (A1 ≈ end of cycle 3 ... B2 ≈ baccalauréat). Final count: **6,051 topics**, validated against a Marble-compatible schema extended with `nameFr`.

## Phase C: Prerequisite graph and clusters

**Edge proposal.** 138 agents (121 same-subject chunks with all same-subject topics offered as candidate prerequisites, plus 17 curated cross-subject pairs such as maths → physique-chimie and français → philosophie) proposed edges under strict rules: real conceptual dependency only, prerequisite never later-aged, entry topics get none, 0-4 per topic, each edge tagged hard/soft with a ≤15-word reason. 10,880 clean proposals.

**Adversarial refutation.** 272 panels of 40 edges each reviewed proposals with a default stance of rejection: thematic association, generic dependencies ("needs reading"), wrong direction, and transitive noise all die. 784 edges rejected (~7%).

**Determinism at the end.** Code enforced the global properties: duplicate and self-loop removal, age-direction re-check after the CECRL re-aging (23 newly inverted edges dropped), and acyclicity by iterative cycle detection, dropping the weakest edge per cycle (14 dropped). Final: **10,050 edges** (4,368 hard / 5,682 soft), a verified DAG.

**Clusters.** 42 agents wrote 845 parent-friendly summaries, one per (subject, domain, age band) with ≥3 topics, in Marble's "your child is learning..." register.

## Quality audits

Beyond the per-stage verification, two whole-dataset audits ran deterministic checks: referential integrity (0 broken links), duplicate ids (0), age sanity per subject (20 false positives correctly attributed to lycée tronc-commun histoire-géographie; the CECRL nulls caught and fixed), language leakage (0), cluster integrity (0 issues), coverage identity (14,314 linked + 235 discarded = 14,549), DAG re-verification, and manifest checksums. All findings were fixed in the dataset, not papered over in the viewer.

## The viewer

The 3D visualization reuses the architecture discovered by inspecting Marble's public page: a single self-contained HTML file with an embedded `graphdata` JSON and a ~14KB dependency-free renderer (2D canvas with hand-rolled 3D projection, painter's-algorithm depth sorting, BFS lineage tracing). The French implementation adds: an age ruler and level-band slicing, subject-family filters, bilingual EN/FR interface, a chronological "play the path" tour with pause/step controls, a measuring auto-framing servo, and three morphing layouts: the ordered subject columns, a constellation nebula (chronology preserved as height), and a waving tricolore flag whose bands are chronological thirds. Layout positions are precomputed (subject-anchored ring plus 50 iterations of edge-spring smoothing in numpy); dot size encodes transitive influence (the largest foundational topic unlocks 1,427 others).

The demo video was produced deterministically: a virtual clock injected into the page, advanced exactly 1/60 s per frame, 900 native-2K screenshots assembled at 60 fps.

## Provenance and licensing

Every standard traces to a named official document with a Bulletin officiel reference and page locator (`sources.json` is the full inventory). Official text is reproduced under Licence Ouverte / Open Licence v2.0 (Etalab), attribution Ministère de l'Éducation nationale. The distillation (topics, edges, clusters, viewer) is original work; the visualization concept is credited to Marble's os-taxonomy, whose schemas this dataset intentionally matches.

## Honest limitations

- Topic descriptions and evidence are English-only by design; French lives verbatim in the standards layer and in topic names.
- Per-year granularity exists only where France defines it (attendus for français/maths/LV/EMC in CP-3e); elsewhere ages are cycle-banded.
- CECRL-derived language topics use milestone-inferred ages, not document-stated ones.
- 255 topics currently have no edges (sparse subjects such as arts options); density there reflects proposal conservatism, not absence of structure.
- The extraction is faithful to what the programmes say, including their unevenness: some subjects enumerate finely, others speak in prose.
