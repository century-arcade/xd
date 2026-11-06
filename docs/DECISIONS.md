# Decisions

A dated log of decisions about the corpus and its policies, newest first. One
entry per decision: what was decided, and why, in a few lines. Earlier
decisions live in the corpus repository's commit history and merge requests.

## 2026-11-06

- **The project home moves into the xd repository.** The policy documents
  and this site now live in `century-arcade/xd` under `docs/`, served at
  https://centuryarcade.org/xd/. `century-arcade/xdcorpus` is archived, with
  redirects to the new addresses. Reasons: one repository for the project;
  the xd repository already has the project's audience; and Saul prefers the
  address.
- **The Hugging Face organization is `century-arcade`**
  (https://huggingface.co/century-arcade), matching the GitHub organization
  and the domain.
- **A DOI through Zenodo.** The Zenodo record describes the corpus as a
  whole, but its files are the policy documents; the corpus stays private.
  CC-BY-4.0 applies to the documents only, not to the puzzles.
- **A statement on AI.** [AI.md](AI.md) says the corpus holds only
  human-made puzzles, discloses the maintainers' own use of AI tools, and
  proposes terms against using derived data or samples to generate
  crosswords for publication. Reason: concern in the crossword community,
  and publishing data on Hugging Face invites it to be consumed by models.
- **Clue and answer data stays public.** `xd-clues.zip` and
  `xd-metadata.zip` remain openly downloadable. Reason: they are already
  published, they do not let a puzzle be rebuilt, and withdrawing them would
  take away data researchers rely on. *(Saul's position.)* The rules for
  derived data are in [DATASETS.md](DATASETS.md).
- **Dataset venues.** Public derived data is published on Hugging Face,
  under one organization, and on Kaggle as an equal home: the same snapshots
  with the same card text, at the same time. The audience is researchers and
  hobbyist programmers alike. Hugging Face also holds the public-domain sets
  and the gated samples; Zenodo holds a record with a DOI for the corpus as a
  whole; GitHub releases keep the public-domain puzzle sets. Samples of
  modern puzzles stay available on request under [ACCESS.md](ACCESS.md), to
  hobbyists and researchers alike, so a gated Hugging Face dataset is the
  same process with a form. See [DATASETS.md](DATASETS.md).

## 2026-11-05

- **A public home for the project.** The corpus gets a public repository,
  `century-arcade/xdcorpus`, holding its policy documents, with the corpus
  itself staying private. Reason: the policies could not be shown to
  prospective contributors, users or institutions while they lived only in
  the private repository. COLLECTION.md and EDITORIAL.md move here; the
  operational documents (CONTRIBUTING.md, REVIEWING.md) stay with the corpus.
  *(Agreed by both maintainers 2026-11-05. The repository name follows the organization's existing unhyphenated names: xdformat, xdcontrib, xdtalk.)*
- **The name is "corpus", not "archive".** The corpus has been cited as the
  xd Crossword Corpus since 2019; "archive" describes the scans and originals
  (the Every Puzzle Project), while "corpus" describes the normalized research
  collection and matches its terms of use.
- **First preservation self-assessment.** Assessed against the Digital
  Preservation Coalition's Rapid Assessment Model, version 3. Results in
  [assessments/dpc-ram-2026.md](assessments/dpc-ram-2026.md). Priorities: a
  second copy of the source archives, a written access policy, a written
  preservation policy, and a yearly repeat.
- **Governance model.** Two maintainers decide; a small group of advisors is
  consulted yearly and has no vote; a successor custodian is to be named.
  See [GOVERNANCE.md](GOVERNANCE.md).
