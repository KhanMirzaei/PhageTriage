from __future__ import annotations

import html
import json
import math
from pathlib import Path

from .models import SampleResult, SequenceRecord


def _esc(value) -> str:
    return html.escape(str(value if value not in (None, "") else "not available"))


def _badge(value: str) -> str:
    cls = "bad" if value in {"EXCLUDE", "FAIL"} else "warn" if value == "REVIEW" else "info" if value == "INFO" else "good"
    return f'<span class="badge {cls}">{_esc(value)}</span>'


def _finding_text(finding) -> str:
    if finding.value not in (None, "", []):
        return str(finding.value)
    if finding.note:
        return finding.note
    return f"Unavailable ({finding.status})"


def _assessment_rows(result: SampleResult) -> str:
    cycle = str(result.replication_cycle.value or "").lower()
    cycle_state = "FAIL" if any(x in cycle for x in ("temperate", "lysogenic", "chronic")) else "PASS" if any(x in cycle for x in ("lytic", "virulent")) else "REVIEW"
    amr_state = "FAIL" if result.amr.value else "PASS" if result.amr.status == "ok" else "REVIEW"
    vf_state = "FAIL" if result.virulence.value else "PASS" if result.virulence.status == "ok" else "REVIEW"
    completeness_state = "PASS" if result.completeness.value == "complete" else "REVIEW"
    assessments = [
        ("Replication cycle", cycle_state, result.replication_cycle.value, "RepliDec"),
        ("Antimicrobial resistance", amr_state, f"{len(result.amr.value)} CARD hit(s)", "Pharokka CARD"),
        ("Virulence factors", vf_state, f"{len(result.virulence.value)} VFDB hit(s)", "Pharokka VFDB"),
        ("Genome completeness", completeness_state, _finding_text(result.completeness), "viralComplete"),
        ("Host prediction", "PASS" if result.host.value else "REVIEW", _finding_text(result.host), "RaFAH"),
        ("Taxonomy", "PASS" if result.taxonomy.value else "REVIEW", _finding_text(result.taxonomy), "taxmyPHAGE"),
        ("Closest classified phages", "INFO", f"{len(result.closest_phages.value)} reported hit(s); status={result.closest_phages.status}", "taxmyPHAGE"),
        ("Genome annotation", "PASS" if result.annotation.status == "ok" else "REVIEW", result.annotation.value, "Pharokka"),
        ("Phage RNA polymerase", "INFO", f"{len(result.rna_polymerase.value)} annotation hit(s)", "Pharokka annotation"),
        ("Genome topology", "REVIEW" if result.topology == "circular_candidate" else "INFO", f"{result.topology}: {result.topology_evidence}", "FASTA metadata/terminal overlap"),
    ]
    return "".join(
        f"<tr><th>{_esc(name)}</th><td>{_badge(state)}</td><td>{_esc(value)}</td><td>{_esc(source)}</td></tr>"
        for name, state, value, source in assessments
    )


def _features(pharokka_root: Path) -> list[dict]:
    features: list[dict] = []
    if not pharokka_root.exists():
        return features
    for path in sorted(pharokka_root.rglob("*.gff")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#"):
                continue
            # Some Pharokka/GFF combinations emit the two characters "\\t"
            # instead of physical tabs. Accept both without weakening the
            # nine-column GFF validation.
            normalized = line.replace("\\t", "\t") if "\t" not in line and "\\t" in line else line
            fields = normalized.rstrip("\t").split("\t")
            if len(fields) < 9 or fields[2].lower() != "cds":
                continue
            try:
                start, end = int(fields[3]), int(fields[4])
            except ValueError:
                continue
            annotation = "\t".join(fields[8:])
            attributes = {}
            for item in annotation.split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    attributes[key.strip().lower()] = value.strip()
            low = annotation.lower()
            category = "other"
            if "card" in low or "antimicrobial resistance" in low or "antibiotic resistance" in low:
                category = "amr"
            elif "vfdb" in low or "virulence" in low:
                category = "virulence"
            elif "rna polymerase" in low or "rnap" in low:
                category = "rnap"
            elif any(word in low for word in ("capsid", "tail", "portal", "terminase", "structural")):
                category = "structural"
            features.append({
                "start": start,
                "end": end,
                "strand": fields[6],
                "category": category,
                "annotation": annotation,
                "locus_tag": attributes.get("locus_tag") or attributes.get("id", ""),
                "function": attributes.get("function", ""),
                "product": attributes.get("product", ""),
            })
        if features:
            break
    return features


def _annotation_table(features: list[dict], limit: int = 25) -> str:
    informative = [
        feature for feature in features
        if feature.get("product") and "hypothetical" not in feature["product"].lower()
    ]
    selected = (informative or features)[:limit]
    if not selected:
        return '<p class="notice">No Pharokka CDS annotations were available.</p>'
    rows = "".join(
        "<tr>"
        f"<td>{_esc(feature.get('locus_tag'))}</td>"
        f"<td>{feature['start']:,}-{feature['end']:,} ({_esc(feature['strand'])})</td>"
        f"<td>{_esc(feature.get('function'))}</td>"
        f"<td>{_esc(feature.get('product'))}</td>"
        "</tr>"
        for feature in selected
    )
    qualifier = "non-hypothetical " if informative else ""
    return (
        f'<p class="caption">Showing {len(selected)} selected {qualifier}CDS annotations '
        f'of {len(features)} total CDS features.</p>'
        '<div class="overview"><table class="annotation"><thead><tr>'
        '<th>Locus</th><th>Coordinates</th><th>Function</th><th>Product</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def genome_svg(record: SequenceRecord, features: list[dict]) -> str:
    label = f"{record.sample} · {record.length:,} bp · {record.topology}"
    colours = {"other": "#43766c", "structural": "#4878a8", "rnap": "#e6a65d", "amr": "#c23b32", "virulence": "#a64583"}
    legend = ''.join(f'<rect x="{80 + i*115}" y="240" width="12" height="12" fill="{colour}"/><text x="{97 + i*115}" y="251" font-size="11">{name}</text>' for i, (name, colour) in enumerate(colours.items()))
    if record.topology.startswith("circular"):
        rings = []
        for feature in features:
            radius = 82 if feature["strand"] != "-" else 67
            circumference = 2 * math.pi * radius
            length = max(1, feature["end"] - feature["start"] + 1) / record.length * circumference
            gap = circumference - length
            offset = -(feature["start"] - 1) / record.length * circumference
            rings.append(f'<circle cx="350" cy="115" r="{radius}" fill="none" stroke="{colours[feature["category"]]}" stroke-width="10" stroke-dasharray="{length:.2f} {gap:.2f}" stroke-dashoffset="{offset:.2f}" transform="rotate(-90 350 115)"><title>{_esc(feature["annotation"])}</title></circle>')
        if not rings:
            rings.append('<circle cx="350" cy="115" r="82" fill="none" stroke="#9aaca7" stroke-width="10"/>')
        return f'''<svg viewBox="0 0 700 270" role="img" aria-label="Circular annotated genome map">{''.join(rings)}<text x="350" y="115" text-anchor="middle">{record.length:,} bp</text><text x="350" y="220" text-anchor="middle">{_esc(label)}</text>{legend}</svg>'''
    glyphs = []
    for feature in features:
        x1 = 60 + (feature["start"] - 1) / record.length * 580
        x2 = 60 + feature["end"] / record.length * 580
        width = max(2, x2 - x1)
        y = 55 if feature["strand"] != "-" else 82
        direction = 1 if feature["strand"] != "-" else -1
        tip = min(7, width / 2)
        if direction == 1:
            points = f"{x1},{y} {x2-tip},{y} {x2},{y+7} {x2-tip},{y+14} {x1},{y+14}"
        else:
            points = f"{x2},{y} {x1+tip},{y} {x1},{y+7} {x1+tip},{y+14} {x2},{y+14}"
        glyphs.append(f'<polygon points="{points}" fill="{colours[feature["category"]]}"><title>{_esc(feature["annotation"])}</title></polygon>')
    return f'''<svg viewBox="0 0 700 270" role="img" aria-label="Linear annotated genome map"><line x1="60" y1="75" x2="640" y2="75" stroke="#9aaca7" stroke-width="3"/>{''.join(glyphs)}<text x="350" y="145" text-anchor="middle">{_esc(label)}</text>{legend}</svg>'''


def write_reports(output: Path, records: list[SequenceRecord], results: dict[str, SampleResult], manifest: dict) -> None:
    report_dir = output / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 2, "manifest": manifest, "samples": [results[r.sample].to_dict() for r in records]}
    (report_dir / "results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    rows = []
    for rec in records:
        r = results[rec.sample]
        rows.append("\t".join(map(str, [r.sample, r.verdict, r.replication_cycle.value or "NA", len(r.amr.value), len(r.virulence.value), r.completeness.value or "NA", r.host.value or "NA", r.taxonomy.value or "NA", r.topology])))
    (report_dir / "summary.tsv").write_text("sample\tverdict\treplication_cycle\tamr_hits\tvirulence_hits\tcompleteness\thost\ttaxonomy\ttopology\n" + "\n".join(rows) + "\n", encoding="utf-8")
    overview_rows = []
    tool_names = {
        "pharokka": "Pharokka annotation / CARD / VFDB / RNAP",
        "replidec": "RepliDec replication cycle",
        "viralcomplete": "viralComplete genome completeness",
        "taxmyphage": "taxmyPHAGE taxonomy / closest phages",
        "rafah": "RaFAH host prediction",
        "phist": "PHIST host prediction",
    }
    run_rows = []
    for key, label in tool_names.items():
        raw = str(manifest.get(key, "not_run"))
        state = "PASS" if raw == "complete" else "REVIEW"
        run_rows.append(f"<tr><th>{_esc(label)}</th><td>{_badge(state)}</td><td>{_esc(raw)}</td></tr>")
    cards = []
    for rec in records:
        r = results[rec.sample]
        features = _features(output / "tools" / "pharokka" / rec.sample)
        closest = r.closest_phages.value[:5] if isinstance(r.closest_phages.value, list) else []
        overview_rows.append(f'''<tr><th><a href="#{_esc(r.sample)}">{_esc(r.sample)}</a></th><td>{_badge(r.verdict)}</td><td>{_esc(r.replication_cycle.value)}</td><td>{_esc(r.completeness.value)}</td><td>{len(r.amr.value)}</td><td>{len(r.virulence.value)}</td><td>{_esc(r.host.value)}</td></tr>''')
        map_note = f"{len(features)} Pharokka CDS feature(s) plotted" if features else "No Pharokka GFF CDS features were available to plot"
        cards.append(f'''<section id="{_esc(r.sample)}"><h2>{_esc(r.sample)} {_badge(r.verdict)}</h2>
<p class="decision"><strong>Decision basis:</strong> {_esc('; '.join(r.reasons))}</p>
<h3>Annotated genome map</h3>{genome_svg(rec, features)}<p class="caption">{_esc(map_note)}. Hover over a feature to see its full annotation.</p>
<h3>Selected CDS annotations</h3>{_annotation_table(features)}
<h3>Assessment checklist</h3><table class="assessment"><thead><tr><th>Assessment</th><th>Status</th><th>Result</th><th>Evidence source</th></tr></thead><tbody>{_assessment_rows(r)}</tbody></table>
<h3>Key genome information</h3>
<div class="grid"><div><b>Replication cycle</b><br>{_esc(r.replication_cycle.value)}</div><div><b>Completeness</b><br>{_esc(r.completeness.value)}</div><div><b>Host (RaFAH)</b><br>{_esc(r.host.value)}</div><div><b>Topology</b><br>{_esc(r.topology)} — {_esc(r.topology_evidence)}</div><div><b>AMR hits</b><br>{len(r.amr.value)}</div><div><b>Virulence hits</b><br>{len(r.virulence.value)}</div><div><b>Phage RNA polymerase hits</b><br>{len(r.rna_polymerase.value)}</div><div><b>Taxonomy</b><br>{_esc(r.taxonomy.value)}</div></div>
<details><summary>Closest classified phages</summary><pre>{_esc(json.dumps(closest, indent=2))}</pre></details>
<p class="raw-links"><a href="../tools/pharokka/{_esc(r.sample)}/">Pharokka files</a> · <a href="../tools/replidec/">RepliDec files</a> · <a href="../tools/viralcomplete/">viralComplete files</a> · <a href="../tools/rafah/">RaFAH files</a> · <a href="../tools/phist/">PHIST files</a> · <a href="../tools/taxmyphage/">taxmyPHAGE files</a></p>
<details><summary>Complete parsed evidence</summary><pre>{_esc(json.dumps(r.to_dict(), indent=2))}</pre></details></section>''')
    page = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PhageTriage Report</title><style>body{{font:16px system-ui;max-width:1180px;margin:auto;padding:28px;background:#f6f4ef;color:#18302b}}h1,h2,h3{{color:#244f46}}section{{background:white;padding:24px;margin:24px 0;border-radius:14px;box-shadow:0 2px 12px #0001}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:10px;border-bottom:1px solid #dce6e2;text-align:left;vertical-align:top}}thead th{{background:#e7f0ed}}.overview{{overflow-x:auto}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.grid>div{{background:#f1f6f4;padding:12px;border-radius:8px}}.badge{{display:inline-block;font-size:.75em;font-weight:700;padding:5px 9px;border-radius:99px;vertical-align:middle;white-space:nowrap}}.bad{{background:#ffd8d2;color:#8b1e12}}.warn{{background:#fff0bf;color:#735600}}.good{{background:#d4f3df;color:#145b2d}}.info{{background:#dcebf7;color:#244d6b}}svg{{display:block;max-width:760px;width:100%;margin:auto}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#176b5a}}.notice{{border-left:5px solid #e6a65d;padding:12px;background:#fff8e8}}.decision{{border-left:5px solid #43766c;background:#f1f6f4;padding:12px}}.caption{{text-align:center;color:#536b65;font-size:.9em}}.raw-links{{margin-top:20px}}@media print{{body{{background:white;padding:0;font-size:10pt}}section{{box-shadow:none;border:1px solid #dce6e2;break-before:page;margin:0 0 12pt}}section:first-of-type{{break-before:auto}}h2,h3,svg,.decision,.caption{{break-inside:avoid}}table{{font-size:8.5pt}}tr{{break-inside:avoid}}details{{display:none}}a{{color:inherit;text-decoration:none}}}}</style></head><body><h1>PhageTriage Report</h1><p class="notice"><b>Research-use-only.</b> This report is an in-silico triage aid, not evidence that a phage is safe or effective for treatment. Candidate phages still require expert review, genome closure/validation, host-range testing, sterility/endotoxin controls, and appropriate regulatory and laboratory evaluation.</p><section><h2>Executive summary</h2><div class="overview"><table><thead><tr><th>Phage</th><th>Overall verdict</th><th>Replication cycle</th><th>Completeness</th><th>AMR hits</th><th>Virulence hits</th><th>Predicted host</th></tr></thead><tbody>{''.join(overview_rows)}</tbody></table></div><h3>Analysis run status</h3><div class="overview"><table><thead><tr><th>Analysis</th><th>Status</th><th>Raw tool status</th></tr></thead><tbody>{''.join(run_rows)}</tbody></table></div><p>A REVIEW status here means that evidence from that tool is unavailable and must never be interpreted as a negative finding.</p><p><a href="summary.tsv">Download summary TSV</a> · <a href="results.json">Download complete JSON evidence</a></p></section>{''.join(cards)}</body></html>'''
    (report_dir / "index.html").write_text(page, encoding="utf-8")
