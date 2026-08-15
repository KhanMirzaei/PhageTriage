from __future__ import annotations

import gzip
import re
from pathlib import Path
from typing import Iterable

from .models import SequenceRecord

DNA = set("ACGTRYSWKMBDHVN")


def _open_text(path: Path):
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")


def safe_name(text: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip().split()[0]).strip("._-") or "contig"
    name, n = base, 2
    while name in used:
        name, n = f"{base}_{n}", n + 1
    used.add(name)
    return name


def read_fasta(path: Path) -> list[SequenceRecord]:
    records: list[SequenceRecord] = []
    used: set[str] = set()
    header: str | None = None
    chunks: list[str] = []

    def emit() -> None:
        if header is None:
            return
        seq = "".join(chunks).replace(" ", "").upper()
        if not seq:
            raise ValueError(f"Empty FASTA record: {header}")
        invalid = sorted(set(seq) - DNA)
        if invalid:
            raise ValueError(f"Invalid nucleotide(s) in {header}: {''.join(invalid)}")
        records.append(SequenceRecord(safe_name(header, used), header, seq))

    with _open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                emit()
                header, chunks = line[1:].strip(), []
            elif header is None:
                raise ValueError("Input is not FASTA: sequence encountered before header")
            else:
                chunks.append(line)
    emit()
    if not records:
        raise ValueError("No FASTA records found")
    return records


def infer_topology(record: SequenceRecord, override: str, min_overlap: int, max_overlap: int) -> None:
    desc = record.description.lower()
    if override in {"linear", "circular"}:
        record.topology = override
        record.topology_evidence = "user-specified --topology"
        return
    if re.search(r"(?:topology[= :]|^|\s)circular(?:\s|$)", desc):
        record.topology = "circular"
        record.topology_evidence = "FASTA header declares circular topology"
        return
    max_k = min(max_overlap, len(record.sequence) // 2)
    for k in range(max_k, min_overlap - 1, -1):
        overlap = record.sequence[:k]
        if overlap == record.sequence[-k:] and len(set(overlap)) >= 3:
            record.topology = "circular_candidate"
            record.terminal_overlap = k
            record.topology_evidence = f"exact {k}-bp terminal overlap; validate with reads/assembly graph"
            return


def write_fasta(records: Iterable[SequenceRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(f">{rec.sample}\n")
            for start in range(0, len(rec.sequence), 80):
                handle.write(rec.sequence[start : start + 80] + "\n")

