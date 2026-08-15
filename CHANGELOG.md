# Changelog

## 0.7.0 - 2026-08-15

- Replaced vHULK with RaFAH as the default phage-only host predictor to avoid
  the AVX/TensorFlow runtime limitation on Apple Silicon.
- Added the RaFAH installer, precomputed-model fetch, wrapper, parser, report
  integration, and automated test coverage.

## 0.6.0 - 2026-08-15

- Replaced PHIST as the default host predictor with vHULK, which predicts host
  genus/species from the phage genome without a user-supplied host collection.
- Kept PHIST support optional for candidate-host genome matching when `--hosts`
  is explicitly supplied.
- Added vHULK output parsing, workflow integration, installer environment, and
  doctor check.

## 0.5.2 - 2026-08-15

- Changed the report heading to “PhageTriage Report”.
- Fixed T4-style Pharokka GFF files containing escaped tab delimiters so CDS
  annotations appear in the genome map and a new selected-annotation table.
- Fixed headerless multi-genome viralComplete parsing so the first phage is no
  longer mistaken for a header row.
- Added the missing `pyarrow` dependency required by taxmyPHAGE's cached
  Parquet results.
- Made omitted PHIST host collections explicit in the report.

## 0.5.1 - 2026-08-15

- Added a guarded one-command uninstaller for the self-contained runtime.
- Added the complete Bam35c reference genome (`NC_005258.1`) as reproducible
  test data with explicit run instructions.
- Added an installation marker so the uninstaller can validate its target.

## 0.5.0 - 2026-08-15

- Standardized the project, Python package, CLI, launcher, report, runtime
  variables, workflow markers, and documentation under the PhageTriage name.
- Adopted the tagline “Genome-first triage of therapeutic phage candidates.”

## 0.4.0 - 2026-08-15

- Added the beginner-friendly `phagetriage.sh` install/doctor/demo/run launcher.
- Added `phagetriage demo` for a real bundled end-to-end example.
- Changed the installer default to the predictable no-space `$HOME/PhageTriageBundle` runtime.
- Improved post-install instructions and automatic runtime discovery.

## 0.3.0 — 2026-08-15

- Added a one-command installer for all workflow tools and databases.
- Added isolated wrappers for Pharokka, RepliDec, viralComplete, PHIST and taxmyPHAGE.
- Added a Snakemake 9 workflow with optional PHIST execution.
- Added explicit Pharokka CARD and VFDB hit-table parsing.
- Added topology-aware annotated genome maps.
- Added executive, per-phage and machine-readable reports.

## 0.2.0

- Replaced the prototype subprocess runner with Snakemake.

## 0.1.0

- Initial Python prototype.
