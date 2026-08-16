# PhageTriage

PhageTriage is a Snakemake workflow for conservative genomic screening of assembled bacteriophage contigs for phage-therapy research.

## Final tool set

- **Pharokka**: phage annotation, CARD antimicrobial-resistance hits, VFDB virulence-factor hits, and annotation-derived phage RNA polymerases.
- **RepliDec**: virulent/lytic, temperate/lysogenic, and chronic replication-cycle prediction.
- **viralComplete**: reference-based phage-genome completeness assessment.
- **RaFAH**: phage-only host-genus prediction from genome-derived protein content and precomputed random-forest models.
- **taxmyPHAGE**: ICTV taxonomy, similarity analysis, and closest classified phages.
- **Python reporting**: evidence gates, topology-aware maps, HTML, JSON, and TSV output.

The deliberately lean workflow does **not** include iPHoP, geNomad, or BACPHLIP. RaFAH is the default phage-only host predictor; PHIST remains optional when a candidate-host genome collection is supplied. taxmyPHAGE provides taxonomy and closest-phage analysis; RepliDec is the sole replication-cycle predictor.

> **Research-use-only.** A computationally acceptable result alone is not evidence that a phage is clinically safe or effective. 

## Quick start

Linux and macOS users can use the same launcher for installation, verification,
the bundled example, and their own genomes:

```bash
git clone https://github.com/YOUR_ACCOUNT/PhageTriage.git
cd PhageTriage

# Install the pipeline, tools, and databases under $HOME/PhageTriageBundle.
bash phagetriage.sh install

# Confirm that every tool is available.
bash phagetriage.sh doctor

# Run a real included example and create an HTML report.
bash phagetriage.sh demo
```

Remove the self-contained installation with:

```bash
bash phagetriage.sh uninstall --yes
```

This removes the runtime, bundled databases, and any results stored inside
`$HOME/PhageTriageBundle`; copy results you want to retain first. It does not
remove the cloned PhageTriage repository.

The demo report is written to:

```text
$HOME/PhageTriageBundle/demo_results/report/index.html
```

Analyze your own FASTA file with one command:

```bash
bash phagetriage.sh run \
  --input phage_contigs.fasta \
  --output /data/phagetriage_results \
  --threads 8
```

RaFAH runs by default and does not require `--hosts`. PHIST can be added as an
optional candidate-host comparison when `--hosts` points to one bacterial or
archaeal genome FASTA per file.

A real complete test genome is included as
`examples/Bam35c_NC_005258.1.fasta`. Test it directly with all configured demo
resources:

```bash
bash phagetriage.sh run \
  --input examples/Bam35c_NC_005258.1.fasta \
  --output "$HOME/phagetriage_bam35c_test" \
  --threads 4
```

## Workflow

```text
input multi-FASTA
       │
       ├── normalize and split contigs
       ├── Pharokka ── annotation, CARD, VFDB, RNA polymerase
       ├── RepliDec ── replication cycle
       ├── viralComplete ── completeness
       ├── RaFAH ── phage-only host prediction
       └── taxmyPHAGE ── taxonomy and closest phages
                         │
                         └── evidence-based HTML/JSON/TSV report
```

Snakemake supplies dependency-aware execution, automatic resumability, per-rule logs, parallel sample processing, Conda deployment, and support for HPC execution profiles.

## Installation

### Install everything with one command

The bundled installer creates separate environments for every tool, installs RaFAH and viralComplete, installs PhageTriage/Snakemake, and downloads the Pharokka and taxmyPHAGE databases:

```bash
bash phagetriage.sh install
```

The default runtime is `$HOME/PhageTriageBundle`. Set `PHAGETRIAGE_PREFIX` to use a
different no-space location:

```bash
PHAGETRIAGE_PREFIX=/data/PhageTriageBundle bash phagetriage.sh install
```

The installation prefix must not contain spaces. The repository itself may be
stored in a path with spaces.
For real analyses, `--output`, `--hosts`, and database paths must also be free
of whitespace because several upstream programs construct unquoted internal
commands. PhageTriage checks these paths before starting. The input FASTA itself
may be stored in a path containing spaces because it is normalized first.

Database downloads can require tens of gigabytes and may take a long time. To install the programs first and download databases later:

```bash
bash phagetriage.sh install --skip-databases
```

Activate the completed bundle:

```bash
source "$HOME/PhageTriageBundle/activate.sh"
phagetriage --version
```

The installer is safe to rerun: existing environments and completed database installations are retained. It requires Conda or Mamba, Git, Make, internet access, and a C++ compiler. On Apple Silicon, the Bioconda environments use the `osx-64` platform and require Rosetta 2.

### Manual wrapper installation

Install the Python package and Snakemake entry point:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Pharokka, RepliDec, taxmyPHAGE, and RaFAH have rule-specific Conda environments. Install viralComplete from its source repository with its BLAST database and provide the executable paths when they are not on `PATH`.

Install the databases required by each upstream tool. For example:

```bash
pharokka install -o /data/pharokka_db
taxmyphage install -db /data/taxmyphage_db
```

RaFAH predicts from phage genomes and reports a host genus with a score. Low-score or missing predictions are reported for review. PHIST is optional and requires a candidate-host genome directory.

## Running

```bash
phagetriage run \
  --input phage_contigs.fasta \
  --output phagetriage_results \
  --hosts candidate_host_genomes/ \
  --pharokka-db /data/pharokka_db \
  --taxmyphage-db /data/taxmyphage_db \
  --viralcomplete /opt/viralComplete/bin/viralcomplete \
  --threads 8 \
  --use-conda
```

Preview the Snakemake DAG without running it:

```bash
phagetriage run -i contigs.fa -o results --hosts hosts --dry-run
```

Resume after an interrupted job:

```bash
phagetriage run -i contigs.fa -o results --hosts hosts --rerun-incomplete
```

Use an HPC execution profile:

```bash
phagetriage run -i contigs.fa -o results --hosts hosts --profile slurm --use-conda
```

For current Snakemake versions, `--use-conda` maps to Snakemake's `--software-deployment-method conda` execution option.

## Evidence rules

PhageTriage does not average biological hazards into an opaque score.

- **EXCLUDE**: RepliDec reports temperate/lysogenic/chronic replication, or Pharokka contains one or more rows in `top_hits_card.tsv` or `top_hits_vfdb.tsv`.
- **REVIEW**: replication cycle is uncertain, viralComplete does not establish completeness, PHIST has no prediction, taxonomy is missing, or circularity is inferred only from terminal overlap.
- **CANDIDATE_FOR_WET_LAB_REVIEW**: all configured computational gates pass. Experimental validation is still required.

Virulence-factor detection is based specifically on Pharokka's VFDB hit table. The complete hit row, source file, coordinates, scores, and annotations are retained as evidence. An empty VFDB table means “no VFDB hit detected under the selected database and thresholds,” not proof that no virulence function exists.

Phage RNA polymerase, taxonomy, closest relatives, and topology are informational; none is independently a safety pass or exclusion.

## viralComplete and topology

viralComplete estimates completeness relative to known viral references. It does not determine genome topology. PhageTriage therefore reports these independently:

- `circular`: explicitly supplied by the user or FASTA metadata.
- `circular_candidate`: exact non-low-complexity terminal overlap detected; read-backed validation required.
- `linear_or_undetermined`: circularity was not established, which is not the same as proving a linear physical genome.

## Output

```text
results/
├── phagetriage.config.json
├── inputs/
├── tools/
│   ├── pharokka/<sample>/
│   ├── replidec/
│   ├── viralcomplete/
│   ├── phist/
│   └── taxmyphage/
├── logs/
└── report/
    ├── index.html
    ├── results.json
    └── summary.tsv
```

All original upstream outputs and logs remain available for manual scientific review.
