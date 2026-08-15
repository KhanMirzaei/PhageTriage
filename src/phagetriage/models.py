from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SequenceRecord:
    sample: str
    description: str
    sequence: str
    topology: str = "linear_or_undetermined"
    topology_evidence: str = "no explicit circularity metadata or terminal overlap"
    terminal_overlap: int = 0

    @property
    def length(self) -> int:
        return len(self.sequence)

    @property
    def gc_percent(self) -> float:
        if not self.sequence:
            return 0.0
        return round(100 * (self.sequence.count("G") + self.sequence.count("C")) / len(self.sequence), 2)


@dataclass
class Finding:
    value: Any = None
    status: str = "not_run"
    evidence: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""


@dataclass
class SampleResult:
    sample: str
    length: int
    gc_percent: float
    topology: str
    topology_evidence: str
    terminal_overlap: int
    replication_cycle: Finding = field(default_factory=Finding)
    amr: Finding = field(default_factory=lambda: Finding(value=[]))
    virulence: Finding = field(default_factory=lambda: Finding(value=[]))
    rna_polymerase: Finding = field(default_factory=lambda: Finding(value=[]))
    completeness: Finding = field(default_factory=Finding)
    host: Finding = field(default_factory=Finding)
    taxonomy: Finding = field(default_factory=Finding)
    closest_phages: Finding = field(default_factory=lambda: Finding(value=[]))
    annotation: Finding = field(default_factory=Finding)
    verdict: str = "REVIEW"
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

