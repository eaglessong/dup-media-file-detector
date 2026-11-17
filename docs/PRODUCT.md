# Product brief

**Status:** Draft — product-owner input welcome

## Goal

Help a person identify duplicate media files in selected local folders while keeping
original files safe. Develop features from human-authored artifacts with agent execution.

## Confirmed by the owner

- Project name: `dup-media-file-detector`.
- Feature work should be driven by design documents and a forge-like agent workflow.

## Proposed starting scope (agent assumptions, not owner decisions)

- A first local, read-only scan that reports exact byte-for-byte duplicates.
- No media uploads, automatic deletion, or moves.
- Perceptual image/video/audio similarity is a later, separately designed feature.

## Please describe in ordinary language

- Who will use this, and what is frustrating about their current process?
- Which OS, media types, and storage locations matter first?
- How many files, roughly how much data, and what scan time is acceptable?
- Would you prefer a CLI, desktop UI, or local web UI?
- Should visually similar or transcoded media count as duplicates?
- What output would make the first version useful?

## Decisions to settle during the first SURVEY

Application language and distribution; first supported OS; user entry point; media
selection rules; symlink policy; result format; scan limits; exact-only first scope.

## Success

Each accepted feature has numbered acceptance criteria, a design with attributed
decisions, executable behavioral tests, a working demonstration, and review evidence.
The owner can request changes through prose and artifacts without editing application code.
