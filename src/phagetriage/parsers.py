from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

from .models import Finding, SampleResult


def _run_status(root: Path, fallback: str) -> str:
    marker = root / ".phagetriage_status"
    if marker.is_file():
        value = marker.read_text(encoding="utf-8", errors="replace").strip()
        return "complete" if value == "complete" else value or "failed"
    return fallback


def _tables(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".tsv", ".csv", ".gff", ".txt"})


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return []
        delim = "\t" if path.suffix.lower() in {".tsv", ".gff"} or text.count("\t") > text.count(",") else ","
        return [{str(k).strip(): str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(text.splitlines(), delimiter=delim)]
    except (csv.Error, OSError):
        return []


def _sample_from_row(row: dict[str, str], samples: set[str]) -> str | None:
    for value in row.values():
        token = value.split()[0] if value else ""
        if token in samples:
            return token
    return None


def parse_replidec(root: Path, results: dict[str, SampleResult], status: str) -> None:
    candidates = list(root.rglob("prediction_summary.tsv")) if root.exists() else []
    for path in candidates:
        for row in _read_rows(path):
            sample = _sample_from_row(row, set(results))
            if not sample:
                continue
            # RepliDec exposes intermediate PFAM/Bayesian calls as well as its
            # integrated final call.  Never let an earlier "Virulent" column
            # mask a final "Temperate" or "Chronic" safety-relevant result.
            lower = {k.strip().lower(): v.strip() for k, v in row.items()}
            preferred = lower.get("final_label", "")
            joined = " | ".join(row.values())
            match = re.search(
                r"\b(virulent|lytic|temperate|lysogenic|chronic)\b",
                preferred or joined,
                re.I,
            )
            results[sample].replication_cycle = Finding(
                value=match.group(1).lower() if match else joined,
                status="ok" if match else "uncertain",
                evidence=[{"source": str(path), "row": row}],
            )
    for result in results.values():
        if result.replication_cycle.status == "not_run":
            result.replication_cycle.status = status


def parse_viralcomplete(root: Path, results: dict[str, SampleResult], status: str) -> None:
    for path in _tables(root):
        if "result_table" not in path.name:
            continue
        # viralComplete 1.x writes a headerless seven-column result table.
        # Always parse that native format explicitly: DictReader silently
        # consumes the first phage as a header when a multi-FASTA has >1 row.
        try:
            raw_rows = list(csv.reader(path.read_text(encoding="utf-8", errors="replace").splitlines()))
        except (csv.Error, OSError):
            raw_rows = []
        if raw_rows and raw_rows[0] and raw_rows[0][0].strip().lower() in {"sample", "query", "contig", "sequence"}:
            raw_rows = raw_rows[1:]
        rows = [
            {
                "sample": raw[0],
                "query_length": raw[1] if len(raw) > 1 else "",
                "coverage": raw[2] if len(raw) > 2 else "",
                "classification": raw[3] if len(raw) > 3 else "",
                "reference": raw[4] if len(raw) > 4 else "",
                "reference_length": raw[5] if len(raw) > 5 else "",
                "description": raw[6] if len(raw) > 6 else "",
            }
            for raw in raw_rows if raw
        ]
        for row in rows:
            sample = _sample_from_row(row, set(results))
            if sample:
                joined = " | ".join(row.values())
                classification = row.get("classification", "")
                result = "complete" if re.search(r"full[- ]length|\bcomplete\b", classification or joined, re.I) and not re.search(r"incomplete|partial|not complete", classification, re.I) else "incomplete_or_uncertain"
                results[sample].completeness = Finding(result, "ok", [{"source": str(path), "row": row}])
    for result in results.values():
        if result.completeness.status == "not_run":
            result.completeness.status = status


def parse_phist(root: Path, results: dict[str, SampleResult], status: str) -> None:
    files = list(root.rglob("predictions.csv")) if root.exists() else []
    for path in files:
        for row in _read_rows(path):
            sample = _sample_from_row(row, set(results))
            if not sample:
                continue
            keys = {k.lower(): k for k in row}
            host = row.get(keys.get("host", "")) or list(row.values())[1] if len(row) > 1 else ""
            results[sample].host = Finding(host, "ok" if host else "uncertain", [{"source": str(path), "row": row}])
    for result in results.values():
        if result.host.status == "not_run":
            result.host.status = status
            result.host.note = (
                "PHIST was not run because no candidate-host genome directory was supplied with --hosts."
                if status == "not_run"
                else f"PHIST host prediction unavailable ({status})."
            )


def parse_rafah(root: Path, results: dict[str, SampleResult], status: str) -> None:
    """Parse RaFAH *_Seq_Info_Prediction.tsv outputs."""
    files = list(root.rglob("*_Seq_Info_Prediction.tsv")) if root.exists() else []
    for path in files:
        rows = _read_rows(path)
        for row in rows:
            sample = _sample_from_row(row, set(results))
            if not sample:
                for key in ("source file", "source_file", "source", "file"):
                    candidate = row.get(key, "")
                    stem = Path(candidate).stem
                    if stem in results:
                        sample = stem
                        break
            if not sample:
                continue
            lower = {k.lower(): v for k, v in row.items()}
            host = lower.get("predicted_host", "")
            score = lower.get("predicted_host_score", "")
            value = f"genus={host}" if host else ""
            results[sample].host = Finding(value, "ok" if value else "uncertain", [{"source": str(path), "row": row, "score": score}])
    for result in results.values():
        if result.host.status == "not_run":
            result.host.status = status
            if status != "complete":
                result.host.note = f"RaFAH host prediction unavailable ({status})."


def parse_taxmyphage(root: Path, results: dict[str, SampleResult], status: str) -> None:
    summaries = list(root.rglob("Summary_taxonomy.tsv")) if root.exists() else []
    for path in summaries:
        for row in _read_rows(path):
            sample = _sample_from_row(row, set(results))
            if not sample:
                continue
            lower = {k.lower(): v for k, v in row.items()}
            taxonomy = lower.get("full classification") or "; ".join(
                f"{rank}={lower[rank]}" for rank in ("realm", "phylum", "class", "order", "family", "subfamily", "genus", "species") if lower.get(rank)
            )
            results[sample].taxonomy = Finding(taxonomy, "ok" if taxonomy else "uncertain", [{"source": str(path), "row": row}])
    for sample, result in results.items():
        sim_files = list((root / "Results_per_genome" / sample).rglob("similarities.tsv")) if (root / "Results_per_genome" / sample).exists() else []
        hits: list[dict[str, str]] = []
        for path in sim_files:
            hits.extend(_read_rows(path)[:10])
        if hits:
            result.closest_phages = Finding(hits, "ok", [{"source": str(sim_files[0])}])
        else:
            result.closest_phages.status = status
        if result.taxonomy.status == "not_run":
            result.taxonomy.status = status


def parse_pharokka(root: Path, results: dict[str, SampleResult], status: str) -> None:
    rnap_re = re.compile(r"\b(?:DNA[- ]directed )?RNA polymerase\b|\bRNAP\b", re.I)
    for sample, result in results.items():
        sample_root = root / sample
        sample_status = _run_status(sample_root, status)
        evidence = []
        amr, vf, rnap = [], [], []
        # Pharokka guarantees that these files contain a header but no data rows
        # when there are no CARD/VFDB hits. Parse them explicitly so database
        # names in unrelated headers cannot become false safety findings.
        for path in sample_root.rglob("*top_hits_card.tsv") if sample_root.exists() else []:
            for row in _read_rows(path):
                amr.append({"source": str(path), "row": row})
        for path in sample_root.rglob("*top_hits_vfdb.tsv") if sample_root.exists() else []:
            for row in _read_rows(path):
                vf.append({"source": str(path), "row": row})
        for path in _tables(sample_root):
            if path.stat().st_size > 50_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), 1):
                if line_no == 1 and path.suffix.lower() in {".tsv", ".csv"}:
                    continue
                if not line.strip() or line.startswith("#"):
                    continue
                item = {"source": str(path), "line": line_no, "text": line[:1000]}
                if rnap_re.search(line):
                    rnap.append(item)
            if path.suffix.lower() in {".gff", ".tsv"}:
                evidence.append({"source": str(path)})
        completed = sample_status == "complete"
        result.amr = Finding(amr, "ok" if completed else sample_status, amr)
        result.virulence = Finding(vf, "ok" if completed else sample_status, vf)
        result.rna_polymerase = Finding(rnap, "ok" if completed else sample_status, rnap)
        result.annotation = Finding("available" if evidence and completed else None, "ok" if evidence and completed else sample_status, evidence)
