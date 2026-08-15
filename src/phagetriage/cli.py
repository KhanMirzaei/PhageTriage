from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__


TOOLS = {"Snakemake": "snakemake", "Pharokka": "pharokka", "RepliDec": "Replidec", "viralComplete": "viralcomplete", "taxmyPHAGE": "taxmyphage", "RaFAH": "RaFAH.py"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="phagetriage", description="Conservative in-silico screening of phage contigs for therapy research")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run analysis and create HTML/JSON/TSV reports")
    run.add_argument("-i", "--input", required=True, help="multi-FASTA phage contigs")
    run.add_argument("-o", "--output", required=True)
    run.add_argument("--hosts", help="directory containing one candidate host genome FASTA per file (required for PHIST)")
    run.add_argument("-t", "--threads", type=int, default=4)
    run.add_argument("--topology", choices=["auto", "linear", "circular"], default="auto")
    run.add_argument("--min-terminal-overlap", type=int, default=20)
    run.add_argument("--max-terminal-overlap", type=int, default=500)
    run.add_argument("--completeness-threshold", type=float, default=0.9)
    run.add_argument("--pharokka-db", default=os.environ.get("PHAGETRIAGE_PHAROKKA_DB"))
    run.add_argument("--taxmyphage-db", default=os.environ.get("PHAGETRIAGE_TAXMYPHAGE_DB"))
    run.add_argument("--pharokka", default="pharokka")
    run.add_argument("--replidec", default="Replidec")
    run.add_argument("--viralcomplete", default="viralcomplete")
    run.add_argument("--taxmyphage", default="taxmyphage")
    run.add_argument("--phist", default="phist.py", help="PHIST phist.py path or executable name")
    run.add_argument("--rafah", default="RaFAH.py", help="RaFAH wrapper path or executable name")
    run.add_argument("--use-conda", action="store_true", help="activate Snakemake per-rule Conda environments")
    run.add_argument("--profile", help="Snakemake execution profile, for example an HPC/SLURM profile")
    run.add_argument("--dry-run", action="store_true", help="show the Snakemake execution plan")
    run.add_argument("--rerun-incomplete", action="store_true")
    demo = sub.add_parser("demo", help="run the installed end-to-end example and create a report")
    demo.add_argument("-o", "--output", help="demo result directory (default: INSTALL_ROOT/demo_results)")
    demo.add_argument("-t", "--threads", type=int, default=4)
    demo.add_argument("--dry-run", action="store_true", help="preview the demo workflow without executing tools")
    demo.add_argument("--rerun-incomplete", action="store_true")
    sub.add_parser("doctor", help="show whether external executables are visible")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "demo":
        install_root_value = os.environ.get("PHAGETRIAGE_INSTALL_ROOT")
        if not install_root_value:
            raise SystemExit(
                "The demo requires the all-in-one installation. Run 'bash phagetriage.sh install' "
                "from the repository, then 'bash phagetriage.sh demo'."
            )
        install_root = Path(install_root_value).resolve()
        virus = install_root / "examples/Bam35c_NC_005258.1.fasta"
        if not virus.is_file():
            raise SystemExit(
                f"Demo data were not found under {install_root}/examples. "
                "Rerun the all-in-one installer to repair the installation."
            )
        demo_output = Path(args.output).resolve() if args.output else install_root / "demo_results"
        forwarded = [
            "run", "--input", str(virus),
            "--output", str(demo_output), "--threads", str(args.threads),
        ]
        if args.rerun_incomplete:
            forwarded.append("--rerun-incomplete")
        if args.dry_run:
            forwarded.append("--dry-run")
        print(f"Running the PhageTriage demo. Results will be written to {demo_output}")
        return main(forwarded)
    if args.command == "doctor":
        missing = False
        for label, exe in TOOLS.items():
            found = shutil.which(exe)
            print(f"{label:14} {'OK: ' + found if found else 'MISSING'}")
            missing |= found is None
        print("Note: RaFAH predicts from phage genomes; optional PHIST matching requires a supplied candidate-host collection.")
        return int(missing)
    if args.threads < 1 or not 0 < args.completeness_threshold <= 1:
        raise SystemExit("--threads must be >=1 and --completeness-threshold must be in (0,1]")
    output = Path(args.output).resolve()
    whitespace_paths = [("--output", output)]
    if args.hosts:
        whitespace_paths.append(("--hosts", Path(args.hosts).resolve()))
    if args.pharokka_db:
        whitespace_paths.append(("--pharokka-db", Path(args.pharokka_db).resolve()))
    if args.taxmyphage_db:
        whitespace_paths.append(("--taxmyphage-db", Path(args.taxmyphage_db).resolve()))
    invalid = [(flag, path) for flag, path in whitespace_paths if any(char.isspace() for char in str(path))]
    if invalid:
        details = ", ".join(f"{flag}={path}" for flag, path in invalid)
        raise SystemExit(
            "PhageTriage output, host, and database paths must not contain whitespace because "
            f"some upstream tools do not safely handle it ({details}). The input FASTA may contain spaces."
        )
    output.mkdir(parents=True, exist_ok=True)
    workflow_config = {
        "input": str(Path(args.input).resolve()), "output": str(output),
        "hosts": str(Path(args.hosts).resolve()) if args.hosts else None,
        "threads": args.threads, "topology": args.topology,
        "min_terminal_overlap": args.min_terminal_overlap,
        "max_terminal_overlap": args.max_terminal_overlap,
        "completeness_threshold": args.completeness_threshold,
        "pharokka_db": str(Path(args.pharokka_db).resolve()) if args.pharokka_db else None,
        "taxmyphage_db": str(Path(args.taxmyphage_db).resolve()) if args.taxmyphage_db else None,
        "executables": {"pharokka": args.pharokka, "replidec": args.replidec,
                        "viralcomplete": args.viralcomplete, "taxmyphage": args.taxmyphage,
                        "rafah": args.rafah,
                        "phist": args.phist},
    }
    config_path = output / "phagetriage.config.json"
    config_path.write_text(json.dumps(workflow_config, indent=2), encoding="utf-8")
    snakefile = Path(__file__).parent / "workflow" / "Snakefile"
    command = ["snakemake", "--snakefile", str(snakefile), "--configfile", str(config_path), "--cores", str(args.threads), "--printshellcmds", "--show-failed-logs"]
    if args.use_conda:
        command += ["--software-deployment-method", "conda"]
    if args.profile:
        command += ["--profile", args.profile]
    if args.dry_run:
        command.append("--dry-run")
    if args.rerun_incomplete:
        command.append("--rerun-incomplete")
    try:
        completed = subprocess.run(command, check=False)
    except OSError as exc:
        print(f"phagetriage: error launching Snakemake: {exc}", file=sys.stderr)
        return 2
    if completed.returncode == 0 and not args.dry_run:
        print(f"Report: {output / 'report' / 'index.html'}")
    return completed.returncode
