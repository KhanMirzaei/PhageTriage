from __future__ import annotations

from .models import SampleResult


def assign_verdict(result: SampleResult) -> None:
    exclusion: list[str] = []
    review: list[str] = []
    cycle = str(result.replication_cycle.value or "").lower()
    if any(term in cycle for term in ("temperate", "lysogenic", "chronic")):
        exclusion.append(f"replication cycle is {result.replication_cycle.value}")
    elif not any(term in cycle for term in ("lytic", "virulent")):
        review.append("lytic/virulent replication cycle not established")
    if result.amr.value:
        exclusion.append(f"{len(result.amr.value)} AMR-related annotation hit(s)")
    elif result.amr.status != "ok":
        review.append("AMR screen unavailable")
    if result.virulence.value:
        exclusion.append(f"{len(result.virulence.value)} virulence-related annotation hit(s)")
    elif result.virulence.status != "ok":
        review.append("virulence screen unavailable")
    if result.completeness.value != "complete":
        review.append("genome completeness not established")
    if not result.host.value:
        review.append("host prediction unavailable")
    if not result.taxonomy.value:
        review.append("taxonomy unavailable")
    if result.topology == "circular_candidate":
        review.append("circularity is inferred from terminal overlap and requires validation")
    if exclusion:
        result.verdict, result.reasons = "EXCLUDE", exclusion + review
    elif review:
        result.verdict, result.reasons = "REVIEW", review
    else:
        result.verdict = "CANDIDATE_FOR_WET_LAB_REVIEW"
        result.reasons = ["all configured in-silico gates passed; experimental validation is still required"]

