# Product brief

**Status:** Draft — product-owner input welcome

## Goal

Help a person identify duplicate media files in selected local folders while keeping
original files safe. Create an inventory of the duplicated files and use the inventory for future operations, for example move the duplicated files to another location.
Develop features from human-authored artifacts with agent execution.

## Confirmed by the owner

- Project name: `dup-media-file-detector`.
- Feature work should be driven by design documents and a forge-like agent workflow.

## Proposed starting scope (agent assumptions, not owner decisions)

- A first local, read-only scan that reports exact byte-for-byte duplicates.
- No media uploads, automatic deletion, or moves.
- Perceptual image/video/audio similarity is a later, separately designed feature.

## Please describe in ordinary language

The utility will be used by the owner of Synology NAS, which offers a Linux-like command line interface.
The files are all stored under a folder with cascading subfolders of a Linux-like file system.
The number of files could be large and the total size could be hundreds of gigabytes. There is no restriction of file scan time.
The utility should be a CLI that can run under a Linux-like shell environment.
The definition of duplicate is that the binary content of two files are exactly yhe same.
The first version should just create an inventiry of all duplicated files under a folder, without changing any of those files.

## Decisions to settle during the first SURVEY

The utility should be written in Python.

## Success

Each accepted feature has numbered acceptance criteria, a design with attributed
decisions, executable behavioral tests, a working demonstration, and review evidence.
The owner can request changes through prose and artifacts without editing application code.

## First-scan SURVEY outcome (2026-11-17)

Owner selected extension-based media filtering, JSON with root-relative paths, group
sizes and errors, and skipping symbolic links while listing hard-linked paths with
shared storage identified. See [attributed decisions](decisions/001-first-scan.md)
and [implementation design](design/first-scan.md). This feature remains read-only.
