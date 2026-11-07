# DPC RAM assessment: the xd Crossword Corpus

Model: Digital Preservation Coalition Rapid Assessment Model, version 3 (March 2024), https://doi.org/10.7207/dpcram24-03

- Organization: the xd Crossword Corpus (a private repository on GitLab), maintained by Saul Pwanson and Alex DeJarnatt
- Assessment completed by: Alex DeJarnatt (drafted with Claude, reviewed by the maintainers)
- Assessment completed on: 2026-11-05
- Scope: the corpus and its tooling (xd pipeline, convert2xd, xdlint, GitLab CI jobs, the nightly download job, the cloud bucket of source archives, xd.saul.pw, The Cross Reference). The Every Puzzle Project is a contributing stream and is assessed separately.
- Time frame for target levels: 3 years (to late 2029)

Levels: 0 Minimal awareness, 1 Awareness, 2 Basic, 3 Managed, 4 Optimized. No half marks: partial fit scores the level below.

## Summary

| | Capability | Current | Target |
|---|---|---|---|
| A | Organizational viability | 2 | 2 |
| B | Policy and strategy | 2 | 3 |
| C | Legal and ethical | 2 | 3 |
| D | IT capability | 2 | 2 |
| E | Continuous improvement | 2 | 3 |
| F | Community | 2 | 2 |
| G | Acquisition, transfer and ingest | 3 | 3 |
| H | Bitstream preservation | 2 | 3 |
| I | Content preservation | 3 | 3 |
| J | Metadata management | 3 | 3 |
| K | Discovery and access | 2 | 3 |

Priorities, in order: H (the only capability where content has actually been lost), then C and K together (one written access and redistribution policy lifts both), then B and E (cheap: a short policy page and a yearly repeat of this assessment).

## Organizational capabilities

### A. Organizational viability — current 2, target 2

Why 2: two maintainers with clear, if informal, division of responsibility and the time to do the work. Hosting (a small server, cloud storage, GitLab) is paid out of pocket, which is a budget of sorts. The level 3 examples (dedicated core budget, regular assessment of roles and budgets, strategic priority) describe an institution, not a two-person volunteer project.

Target 2. Worth doing anyway, without changing the score: a one-paragraph continuity note in the repo stating that if either maintainer stops, the other carries on, and naming a fallback custodian (an institution or a third person) for the corpus and the source archives should both stop. Today this is assumed but not written.

### B. Policy and strategy — current 2, target 3

Why 2: scope of collection is defined (COLLECTION.md), procedures for ingest, review, editing and provenance are documented (CONTRIBUTING.md, REVIEWING.md, EDITORIAL.md, AGENTS.md), and conventions are tagged established / practice / proposed. Permitted use is stated in the README. What is missing is the level 2 anchor and the level 3 requirement: a high-level preservation policy or strategy, and a review schedule for the documents.

To reach 3: a short PRESERVATION.md (or a section of README) stating what the corpus commits to: keep every puzzle ever accepted, in plain-text .xd, with its provenance; where the copies live; how long (indefinitely); how edits are recorded (git history, no rewrites). Review the policy documents on a schedule (once a year, alongside this assessment). Note the ethical positions already taken, such as the Trans Metadata Collective naming policy, as policy rather than practice.

### C. Legal and ethical — current 2, target 3

Why 2: rights holders are identified per puzzle (Copyright: header, publications.tsv), the corpus is private because of copyright, the README states terms of use (research only, no redistribution) and a citation request, and receipts rules exclude private data. Access grants and partial-data grants (clue and answer pairs, a random sample) have been made on judgment, with terms stated verbally, and none of it is documented.

To reach 3: write the access and redistribution policy: what can be shared with whom (full corpus, derived data such as clue and answer pairs, public aggregate statistics), the standard terms a grantee agrees to, and a log of who was granted what and when. Decide and document how a takedown or rights-holder complaint is handled. The October 2026 data-artifacts tiering plan (public, derived, restricted) is most of the design already.

### D. IT capability — current 2, target 2

Why 2: a private GitLab project with CI and scheduled jobs, a mirror on GitHub, a small server running the nightly download, cloud storage buckets, local clones. Systems are documented at a basic level across CONTRIBUTING.md, REVIEWING.md and .gitlab-ci.yml. Patching the server and management of the third-party accounts are informal.

Target 2. Low-cost improvement without changing the score: one page listing every piece of infrastructure, who holds the account, what it costs and what breaks if it goes away.

### E. Continuous improvement — current 2, target 3

Why 2: this is the first capability assessment, and gaps have been identified.

To reach 3: share this assessment with Saul and agree the targets; repeat it yearly; keep a short roadmap of the agreed actions and tick them off.

### F. Community — current 2, target 2

Why 2: the corpus is deeply embedded in the crossword-data community (open xd format, converters, The Cross Reference, EPP, contributors via Discord and merge requests), but this capability means the digital preservation community, where engagement is just beginning. Contacts and events are accessible and there is a commitment to learn.

Target 2. If a specific need arises (advice on storage, on rights, or on finding an institutional home), the DPC's Level up with DPC RAM pages and the NDSA Levels of Preservation are the places to start.

## Service capabilities

### G. Acquisition, transfer and ingest — current 3, target 3

Why 3: a documented, largely automated ingest process (nightly downloads, convert2xd, receipts.tsv), guidance for contributors (CONTRIBUTING.md, README), appraisal against a written collection policy as a standard part of review, integrity checking on transfer (sha256 of each source archive given in the MR and verified by make-source-archive.py --verify, manifest checksums), and CI checks on every merge request. Stakeholder relationships are managed through Discord and the MR process.

Target 3. Level 4 asks for periodic reappraisal and integrations with source systems, which is not a priority.

### H. Bitstream preservation — current 2, target 3

Why 2: checksums exist for all content (git object hashes for the corpus, sha256 manifests and the archive register for source archives), the corpus is replicated (GitLab project, several contributors' forks, a GitHub mirror, local clones on several machines), the weekly check-source-archives job and source-archives-drift.py detect archives missing or changed in the bucket, and access is restricted to known people. But the raw source archives have a single copy, in a single cloud bucket, and the pre-2025 .puz zips were lost. There is no written storage risk assessment, the GitHub mirror and local clones are not a deliberate backup regime, and nothing has ever been restored from a backup as a test. By the no-half-marks rule this is 2.

To reach 3:
1. A second, independent copy of the source archives (another provider or region, or an offline disk refreshed on a schedule), with object versioning on and a check that both copies agree.
2. A deliberate second copy of the corpus that is not a working clone: an automatic mirror of the corpus repository's master branch (or a nightly bundle to cloud storage), and a note on how to restore it.
3. A written storage risk assessment: what copies exist, where, what each protects against (account loss, provider loss, human error, ransomware), and how often integrity is checked.
4. A restore test once a year: rebuild a working corpus from the mirror and a source archive from the second copy, and record that it worked.

### I. Content preservation — current 3, target 3

Why 3: the whole design is content preservation. Plain-text .xd with a published spec; formats identified and content characterized at import and corpus-wide (xdlint, the corpus checks, corpus-report); quality problems found and tracked (encoding damage, blank clues, placeholder grids, missing answers); preservation actions (re-import with decode fixes, overrides.tsv, header sweeps) recorded in git with who, when, what and why; editorial conventions that state which properties must be kept (the puzzle as the publisher meant it, originals never edited); the needs of current users (research, solvers, tooling) understood. Preservation watch is informal, but the format choice makes it low-risk.

Target 3. Several level 4 examples already hold (version control, quality control on actions). Not a priority to push further.

### J. Metadata management — current 3, target 3

Why 3: persistent unique identifiers (xdids) with written rules for assignment and change; a minimum header set enforced by lint and review (Title, Author, Date, Copyright, Editor, Number); controlled vocabularies (publications.tsv, pubregex.tsv); item-level provenance (receipts.tsv, source archives with NOTES.md); structural relationships between puzzle, receipts and source archive maintained. The metadata standard is the corpus's own rather than an external schema, which is appropriate for the content.

Target 3. Possible later: a mapping from xd headers to a standard schema (Dublin Core or schema.org) for the public derived datasets, which would help the exit strategy and reuse.

### K. Discovery and access — current 2, target 3

Why 2: discovery exists (xd.saul.pw, The Cross Reference with search), users can access the corpus once granted, permitted use is stated in the README, and the GitLab member list records who has access. Access decisions are made case by case on the merits of the project, and partial access (derived data, samples) has been given, but the process and the grants are not written down, and no usage statistics are kept.

To reach 3: document the access process (how to ask, what is considered, what forms of access exist), keep the grant log from capability C, and state the terms on the discovery sites as well as in the README. Mass extraction for an exit strategy is trivially a git clone, which already satisfies that example.
