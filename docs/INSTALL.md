# Installation

## Supported systems

The all-in-one installer targets Linux and macOS. It requires Conda or Mamba, Git, Make, a C++ compiler, internet access and substantial free disk space.

Apple Silicon uses Intel (`osx-64`) Bioconda environments and therefore requires Rosetta 2.

## One-command installation

```bash
bash phagetriage.sh install
```

After installation, verify and run the included real-genome test with:

```bash
bash phagetriage.sh doctor
bash phagetriage.sh demo
```

The easy launcher installs to `$HOME/PhageTriageBundle` by default and calls the
installed commands without requiring shell activation. To choose another
runtime location, set `PHAGETRIAGE_PREFIX` consistently when installing and
running:

```bash
export PHAGETRIAGE_PREFIX=/data/PhageTriageBundle
bash phagetriage.sh install
bash phagetriage.sh doctor
```

Conda-generated launchers require an installation prefix without spaces. The
repository may still live in a folder containing spaces; point `--prefix` to a
separate no-space location.

The same upstream limitation applies to analysis `--output`, `--hosts`, and
database paths. PhageTriage rejects these paths early rather than allowing a
partial, misleading run. Input FASTA paths may contain spaces.

The installer creates isolated environments for PhageTriage/Snakemake, Pharokka, RepliDec, taxmyPHAGE, viralComplete and RaFAH. RaFAH uses its Perl/R environment with Prodigal, HMMER and the precomputed host models. viralComplete is cloned and executed with a dedicated environment containing BLAST, Biopython and Prodigal. PHIST is optional and not part of the default installation.

The Pharokka and taxmyPHAGE databases are downloaded by default. To defer the large database downloads:

```bash
bash phagetriage.sh install --skip-databases
```

The installer is idempotent: it retains existing environments and database installations marked complete.

## Verification

```bash
bash phagetriage.sh doctor
bash phagetriage.sh demo
python -m unittest discover -s tests -v
make dry-run
```

The supplied `make dry-run` writes its temporary plan beneath `/tmp` so it also
works when the cloned repository path contains spaces.

`phagetriage doctor` checks the active `PATH`. The easy launcher configures the
installed wrapper path automatically. Advanced users can alternatively run
`source "$HOME/PhageTriageBundle/activate.sh"` and then call `phagetriage` directly.

## Uninstalling

The installation is self-contained under the selected prefix. Copy any desired
results first, then use the guarded uninstaller:

```bash
bash phagetriage.sh uninstall --yes
```

For a custom prefix, use the same setting used during installation:

```bash
PHAGETRIAGE_PREFIX=/data/PhageTriageBundle bash phagetriage.sh uninstall --yes
```

The uninstaller verifies the target before removing it and refuses `/`, the
user home directory, or a directory that is not recognizable as a PhageTriage
installation. It does not remove the cloned source repository.
