---
name: build-curriculum-taxonomy
description: Build an os-taxonomy-style curriculum taxonomy for any country or education system, from official curriculum documents to verbatim standards, deduplicated micro-topics, a verified prerequisite DAG, parent-friendly clusters, and an interactive 3D viewer. Trigger when the user wants to replicate os-taxonomy-fr for another country, region, or curriculum.
---

# Build a curriculum taxonomy for any country

You are going to turn a country's official curriculum into a connected graph of learning. This repo is the worked example (France, `v1-fr`): 127 source documents became 14,549 verbatim standards, 6,051 micro-topics, 10,050 verified prerequisite links, and 845 domain clusters, all explorable in a self-contained 3D viewer. `METHODOLOGY.md` is the full narrative account of that run; this skill is the operational recipe.

Target outputs, schema-compatible with `schema/` in this repo (and with Marble's os-taxonomy):

| File | Contents |
|---|---|
| `data/sources.json` | Verified official source documents with URLs, direct file links, official references, in-force status |
| `data/{cc}-curriculum-standards.json` | Verbatim standards extracted from the sources |
| `data/{cc}-topics.json` | Deduplicated micro-topics distilled from the standards |
| `data/{cc}-dependencies.json` | Prerequisite edges, a verified DAG |
| `data/{cc}-clusters.json` | Parent-friendly summaries per (subject, domain, age band) |
| `data/{cc}-manifest.json` | Counts and SHA-256 checksums |
| `viewer.html` | `viewer-template.html` + your graphdata, via `scripts/inject_viewer_data.py` |

`{cc}` is the country code (`fr`, `de`, `es`, ...).

## Operating principles (read before starting)

1. **Agents propose, code disposes.** Use LLM agents only for judgment calls (what a standard says, whether two topics are the same idea, whether a prerequisite is real), in small verifiable units. Enforce every global constraint deterministically in code: coverage accounting, merge bookkeeping, acyclicity, schema validity. Never let an agent assert a global property.
2. **Disk-first resumability.** Every agent writes its result to its own file the moment it finishes. Work generators diff the target list against what is already on disk and emit only the missing units. Interrupted runs then cost nothing to resume, and you never re-pay for completed work. Do not build a pipeline that only reports results in memory.
3. **Verbatim or nothing.** Standards carry the official text exactly as written, in the source language, with a locator (page or section) and the official reference (gazette number, decree, edition). Translation and simplification happen at the topic layer, never at the standards layer.
4. **Adversarial verification for anything subjective.** Extractions get fidelity checks against the source. Merge candidates get judge panels. Proposed prerequisite edges face refuters whose default is rejection. One agent's opinion is a proposal; survival under attack is the acceptance criterion.
5. **Pin everything up front.** Country, tracks included, the exact in-force date, subject scope, output languages, and ID conventions. Curricula change every year; an unpinned corpus rots mid-build.

## Phase 0: lock the scope

Ask the user to decide, and record the decisions in the README of the new dataset:

- Education system and track scope (e.g. France voie generale only; decide what you do with vocational tracks, electives, regional variants).
- The date pin: "programmes in force at {date}". Everything is verified against this.
- Age range and how national grade names map to ages (build the equivalent of PS through Terminale mapping to 3..18).
- Output languages: native verbatim always; add an English name/description layer if the user wants international usability (the FR set carries `name` in English plus `nameFr`).
- ID conventions: stable, human-readable slugs. Keep them short; overly long slugs caused a real collision in the FR run when two documents truncated to the same 80-character ID.

## Phase 1: corpus

Goal: every official document that defines the curriculum, downloaded, verified in force at the pin date, and catalogued in `sources.json`.

1. Map the publishing landscape first: which ministry/agency publishes programmes, where consolidated versions live, what the official gazette is (the FR equivalents: eduscol, Bulletin officiel, legifrance).
2. Build the document list per (level, subject), then hunt URLs. Expect anti-bot walls on ministry sites (Datadome, Cloudflare). What worked for France, in order of preference: plain `curl` with browser-ish headers (TLS fingerprint blocking hits python-requests harder than curl), the ministry's static file stores (paths like `/sites/default/files/`), national open-data mirrors (`static.data.gouv.fr` equivalents), and regional academy mirrors of the same PDFs.
3. For every document record: id, title, level(s), subject, the page URL, the direct PDF URL, the official reference, in-force status at the pin date, and SHA-256 of the downloaded file.
4. **Gate:** a validation script confirms every entry downloads, checksums match, and every (level, subject) cell in your scope grid is covered or explicitly marked out of scope.

## Phase 2: verbatim standards extraction

Goal: `{cc}-curriculum-standards.json`, one record per atomic requirement, exactly as the official text states it.

1. For each document, first have a mapper agent produce a **unit chart**: the list of extraction units (chapter, cycle, theme) with page ranges. Store one chart file per document. Instruct mappers to echo the document id exactly as given (agents love to invent their own slugs, which silently breaks matching; give them the literal string and say "echo this exactly").
2. Fan out extraction agents, one unit each. Each agent reads its pages and emits standards records: id, verbatim `text`, subject, domain heading, grade level(s), kind, page locator, official reference. Build the `kind` vocabulary from the country's own curriculum grammar (for France: attendu, competence, connaissance, capacite, objectif, repere).
3. Run **fidelity verifiers** on a sample per document (10 to 20 percent): the verifier re-opens the source pages and checks the extracted text is verbatim, correctly located, and not summarized. Documents failing verification get re-extracted, not patched.
4. **Gate (code):** per-document coverage accounting. Every unit in the chart has an extraction file; totals add up; no duplicate IDs; every record schema-validates against `schema/curriculum-standards.schema.json`.

## Phase 3: micro-topics

Goal: `{cc}-topics.json`. A micro-topic is a **single teachable idea** ("Adding fractions with the same denominator"), not a chapter and not a lesson plan.

1. Atomization agents work per (subject, level) slice of standards. Each topic carries: id, `name` (and the native-language name), a 1-2 sentence description, type (conceptual / procedural / representational / language / meta), subject, domain, age range, 3-6 observable mastery-evidence bullets, and `standardIds` links to every standard it was distilled from.
2. Ages must be real numbers for every topic. Watch for structural traps: the FR language curricula are proficiency-based (CEFR levels), not grade-based, and a naive default gave 3-year-olds essay-writing topics. Build an explicit mapping for such cases (FR used Pre-A1 to C1 milestone ages) and **assert no null or defaulted ages in code**.
3. Deduplicate across slices with an embedding gate plus judge panels:
   - Embed name+description for all topics (FR used gemini-embedding-001, 768 dims, batched; any strong embedding model works, but calibrate on a hand-labeled sample of 50 pairs first).
   - Candidate pairs above cosine ~0.86 within a subject, ~0.90 across subjects (FR-calibrated; re-calibrate for your language).
   - A judge panel (3 independent agents) rules same-idea vs distinct on each candidate pair; majority wins. Judges see names, descriptions, ages, and evidence bullets.
   - **Code performs the merges** with a union-find, remaps every `standardIds` reference, and keeps a merge log.
4. **Gate (code):** coverage identity. `standards covered by kept topics + standards on merged-away duplicates = all extracted standards` (the FR identity was 14,314 + 235 = 14,549). Plus: schema validation, no null ages, no orphan standardIds.

## Phase 4: prerequisite DAG

Goal: `{cc}-dependencies.json`, edges `topic X depends on prerequisite Y`, tagged `hard`/`soft`, each with a one-line reason.

1. Proposal agents work per topic neighborhood: given a topic and a candidate pool (same subject earlier ages, plus cross-subject candidates from the embedding index), propose at most ~5 prerequisites with strength and reason. Bound the pool; do not show an agent 6,000 topics.
2. **Refutation panels** attack every proposed edge: "argue this dependency is false, circular, trivial, or merely thematic; default to refuted when uncertain". An edge survives only if a majority of refuters fail to kill it. This default-reject stance is what keeps the graph honest; skipping it produces plausible-but-wrong chains everywhere.
3. **Code enforces acyclicity**: build the graph, find strongly connected components, and break cycles deterministically (drop the weakest edge in the cycle: soft before hard, then lowest refuter confidence). Log every dropped edge.
4. **Gate (code):** the final file is a proven DAG (topological sort succeeds), edge endpoints all exist, age direction is sane for hard edges (prerequisite age <= dependent age, with a small documented tolerance), and orphan rate (topics with no edges at all) is reported, not hidden.

## Phase 5: clusters

For each (subject, domain, age band): one parent-friendly paragraph summarizing what a child learns there, written from the topics in the cluster. Store topic ID lists per cluster so the summary is auditable. This is a straightforward fan-out; verify counts in code (every topic belongs to exactly one cluster).

## Phase 6: manifest and final audit

1. `{cc}-manifest.json`: record counts per file, per-subject topic counts, and SHA-256 checksums of every data file.
2. Schema-validate everything against `schema/`.
3. Spot-check protocol before shipping: read the 20 highest-degree topics end to end; random-sample 30 standards against their source PDFs for verbatim fidelity; scan every (subject, age) extreme for content that cannot belong there (the age-3 essay class of bug); click through the viewer in every mode.

## Phase 7: the viewer

`viewer-template.html` is the complete self-contained renderer (no dependencies, FR/EN UI, three morphing layouts, lineage tracing, mobile performance governor). You only build the data payload.

Graphdata contract (also in the template's header comment):

```
{
  "groups": ["Mathematics", ...],      // subject-family display names
  "gcol":   ["#4E7FE8", ...],          // one hex color per family
  "H": 1400, "ageMin": 3, "ageMax": 18,
  "nodes": [{
    "x": 0.0, "z": 0.0,                // layout plane position
    "y": 700,                          // vertical: (age-ageMin)/(ageMax-ageMin)*H
    "g": 0,                            // family index into groups
    "a": 7,                            // age (years)
    "c": 0.3,                          // centrality 0..1 (dot size)
    "col": "#4E7FE8",                  // usually gcol[g]
    "dm": "Fractions",                 // domain label
    "t": "Adding fractions...",        // name (viewer language 1)
    "tf": "Additionner des...",        // name (viewer language 2)
    "q": "one-line description",
    "ev": ["mastery bullet", ...]
  }],
  "edges": [[dependentIdx, prereqIdx, hardFlag01], ...]
}
```

Layout recipe that produced the FR graph: anchor each subject family on a ring (angle per family, radius by family size), place topics near their family anchor with jitter, then relax with ~50 iterations of edge-spring smoothing (pull edge endpoints together in x/z only; y stays pinned to age). Centrality `c` = normalized transitive descendant count raised to 0.7. Then:

```bash
python3 scripts/inject_viewer_data.py viewer-template.html graphdata.json my-viewer.html
```

Update the title, subtitle, level-band names, and the flag layout (the third mode is a tricolore; re-color or disable it for your country) directly in the template's i18n block and band definitions.

## Scale and cost reference (the France run)

Three days of orchestrated agent pipelines, roughly 1,700 agent runs, a few hundred dollars of model spend at 2026 prices. The expensive phases are extraction and edge refutation; the cheap insurance everywhere is disk-first resumability, which made several mid-run interruptions free to recover. Budget most of your own attention for Phase 1 (finding trustworthy in-force sources) and the Phase 3/4 verification gates; everything else is throughput.

## Licensing your dataset

Official curriculum text usually falls under a national open licence (France: Licence Ouverte 2.0). Reproduce the verbatim layer under that licence with per-document references in `sources.json`, and license your original layers (topics, edges, clusters, tooling) permissively (this repo uses MIT).
