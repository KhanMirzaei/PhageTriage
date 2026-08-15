from pathlib import Path

from phagetriage.fasta import infer_topology, read_fasta
from phagetriage.models import SampleResult
from phagetriage.parsers import parse_pharokka, parse_phist, parse_rafah, parse_replidec, parse_taxmyphage, parse_viralcomplete
from phagetriage.report import write_reports
from phagetriage.scoring import assign_verdict

out = Path(snakemake.params.out)


def run_status(path: Path, configured: bool = True) -> str:
    if not configured:
        return "not_run"
    marker = path / ".phagetriage_status"
    if marker.is_file():
        return marker.read_text(encoding="utf-8", errors="replace").strip() or "failed"
    return "missing"


records = read_fasta(Path(snakemake.params.original))
for record in records:
    infer_topology(record, snakemake.params.topology, int(snakemake.params.min_overlap), int(snakemake.params.max_overlap))
results = {r.sample: SampleResult(r.sample, r.length, r.gc_percent, r.topology, r.topology_evidence, r.terminal_overlap) for r in records}
statuses = {
    "pharokka": "complete" if all(run_status(out / "tools/pharokka" / sample) == "complete" for sample in results) else "failed_or_missing",
    "replidec": run_status(out / "tools/replidec"),
    "viralcomplete": run_status(out / "tools/viralcomplete"),
    "taxmyphage": run_status(out / "tools/taxmyphage"),
    "rafah": run_status(out / "tools/rafah"),
    "phist": run_status(out / "tools/phist", bool(snakemake.params.phist_enabled)),
}
parse_replidec(out / "tools/replidec", results, statuses["replidec"])
parse_viralcomplete(out / "tools/viralcomplete", results, statuses["viralcomplete"])
parse_taxmyphage(out / "tools/taxmyphage", results, statuses["taxmyphage"])
parse_pharokka(out / "tools/pharokka", results, statuses["pharokka"])
parse_phist(out / "tools/phist", results, statuses["phist"])
parse_rafah(out / "tools/rafah", results, statuses["rafah"])
for result in results.values():
    assign_verdict(result)
manifest = {
    "workflow": "snakemake",
    **statuses,
}
write_reports(out, records, results, manifest)
