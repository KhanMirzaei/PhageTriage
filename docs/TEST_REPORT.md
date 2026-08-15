# Validation report

PhageTriage 0.7.0 validation was performed on 2026-08-15 on Apple Silicon macOS using the
all-in-one installation at `/Users/ali/Documents/Codex/PhageTriageBundle`.

## Automated checks

- Installer syntax and every generated wrapper passed `bash -n`.
- The guarded uninstaller removed a test bundle and refused an unrelated directory.
- The included Bam35c FASTA was validated as one 14,935 bp record.
- All 14 Python unit tests passed.
- The complete Snakemake DAG passed a dry-run with Snakemake 9.23.1.
- `phagetriage doctor` found all six default entry points: Snakemake, Pharokka,
  RepliDec, viralComplete, taxmyPHAGE, and RaFAH.
- The RaFAH model database was not downloaded during this verification update;
  it is fetched by a normal install without `--skip-databases`.
- The beginner-facing demo command is wired to the installed RaFAH stack.

## Full integration test

The report/parser integration was tested with the bundled complete Bacillus
phage Bam35c genome (`NC_005258.1`, 14,935 bp). RaFAH is the default phage-only
host predictor; PHIST is retained only as an optional candidate-host mode.

| Component | Result |
|---|---|
| Pharokka 1.10.0 | Completed; annotation plus CARD/VFDB screens parsed |
| RepliDec 0.3.5 | Completed; final label `Chronic` |
| viralComplete | Completed; `Full-length` parsed as complete |
| RaFAH | Installed and wired as the default; output parser and report integration covered by the automated tests |
| taxmyPHAGE 0.3.7 | Upstream error for this genome; recorded as `failed:1` and REVIEW |
| Report | Generated HTML, JSON, TSV, and linear annotated genome map |

The conservative final verdict for this test genome was **EXCLUDE**, driven by
RepliDec's final chronic-cycle call. The unavailable taxmyPHAGE result was also
listed for review; it was not treated as a negative finding. taxmyPHAGE found a
Mash relative but its current VMR mapping returned no genus and the upstream
program raised an `IndexError`. PhageTriage preserved the log, completed the
remaining analyses, and displayed the failed tool status in the report.

This validates software integration and reporting behavior, not clinical
safety or efficacy. In-silico screening cannot replace genome closure,
phenotypic host-range and transduction testing, sterility/endotoxin testing,
manufacturing controls, or expert and regulatory review.
