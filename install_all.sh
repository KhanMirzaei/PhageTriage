#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${PHAGETRIAGE_PREFIX:-${HOME}/PhageTriageBundle}"
INSTALL_DATABASES=1

usage() {
    printf '%s\n' \
        "Usage: bash install_all.sh [--prefix PATH] [--skip-databases]" \
        "" \
        "Installs PhageTriage, Snakemake, Pharokka, RepliDec, viralComplete," \
        "taxmyPHAGE, and RaFAH into isolated environments below PATH." \
        "Database installation is enabled by default and may require tens of GB." \
        "Default PATH: \$HOME/PhageTriageBundle (override with --prefix or PHAGETRIAGE_PREFIX)."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            [[ $# -ge 2 ]] || { printf '%s\n' "--prefix requires a path" >&2; exit 2; }
            INSTALL_PREFIX="$2"
            shift 2
            ;;
        --skip-databases)
            INSTALL_DATABASES=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "${INSTALL_PREFIX}" =~ [[:space:]] ]]; then
    printf '%s\n' "Installation prefix must not contain spaces because Conda-generated launchers cannot run from such paths." >&2
    printf 'Choose a no-space runtime path, for example:\n  bash install_all.sh --prefix %q\n' "${PROJECT_ROOT%/*}/PhageTriageBundle" >&2
    exit 2
fi

INSTALL_PREFIX="$(mkdir -p "${INSTALL_PREFIX}" && cd -- "${INSTALL_PREFIX}" && pwd)"

for required in git make curl; do
    command -v "$required" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "$required" >&2
        exit 1
    }
done

if command -v mamba >/dev/null 2>&1; then
    CONDA_COMMAND="$(command -v mamba)"
    SOLVER_ARGS=()
elif command -v conda >/dev/null 2>&1; then
    CONDA_COMMAND="$(command -v conda)"
    SOLVER_ARGS=(--solver libmamba)
else
    printf '%s\n' "Conda or Mamba is required. Install Miniforge, then rerun this command." >&2
    printf '%s\n' "https://github.com/conda-forge/miniforge" >&2
    exit 1
fi

mkdir -p "${INSTALL_PREFIX}/envs" "${INSTALL_PREFIX}/src" "${INSTALL_PREFIX}/bin" "${INSTALL_PREFIX}/databases"
printf 'PhageTriage self-contained installation\n' > "${INSTALL_PREFIX}/.phagetriage-installation"

BIO_PLATFORM=()
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    BIO_PLATFORM=(--platform osx-64)
    printf '%s\n' "Apple Silicon detected: creating Intel Bioconda environments. Rosetta 2 is required."
fi

create_env() {
    local env_path="$1"
    shift
    if [[ -x "${env_path}/bin/python" ]]; then
        printf 'Keeping existing environment: %s\n' "$env_path"
        return
    fi
    "${CONDA_COMMAND}" create -y -p "$env_path" "${SOLVER_ARGS[@]}" --override-channels -c conda-forge -c bioconda "$@"
}

printf '%s\n' "Installing workflow environments under ${INSTALL_PREFIX}/envs"
create_env "${INSTALL_PREFIX}/envs/phagetriage" python=3.12 pip snakemake=9.23.1
create_env "${INSTALL_PREFIX}/envs/pharokka" "${BIO_PLATFORM[@]}" pharokka=1.10.0
create_env "${INSTALL_PREFIX}/envs/replidec" "${BIO_PLATFORM[@]}" replidec=0.3.5
create_env "${INSTALL_PREFIX}/envs/taxmyphage" "${BIO_PLATFORM[@]}" taxmyphage
create_env "${INSTALL_PREFIX}/envs/viralcomplete" "${BIO_PLATFORM[@]}" python=3.11 biopython blast prodigal
create_env "${INSTALL_PREFIX}/envs/rafah" "${BIO_PLATFORM[@]}" perl r-base r-ranger perl-bioperl hmmer prodigal

if ! "${INSTALL_PREFIX}/envs/taxmyphage/bin/python" -c 'import pyarrow' >/dev/null 2>&1; then
    printf '%s\n' "Installing taxmyPHAGE Parquet support (pyarrow)..."
    "${CONDA_COMMAND}" install -y -p "${INSTALL_PREFIX}/envs/taxmyphage" "${SOLVER_ARGS[@]}" \
        --override-channels -c conda-forge -c bioconda pyarrow
fi

"${INSTALL_PREFIX}/envs/phagetriage/bin/python" -m pip install --no-deps --upgrade "${PROJECT_ROOT}"

if [[ ! -d "${INSTALL_PREFIX}/src/viralComplete/.git" ]]; then
    git clone https://github.com/ablab/viralComplete.git "${INSTALL_PREFIX}/src/viralComplete"
fi

if [[ ! -s "${INSTALL_PREFIX}/src/RaFAH/RaFAH_v0.2.pl" ]]; then
    mkdir -p "${INSTALL_PREFIX}/src/RaFAH"
    curl -L --fail --retry 3 -o "${INSTALL_PREFIX}/src/RaFAH/RaFAH_v0.2.pl" "https://sourceforge.net/projects/rafah/files/RaFAH_v0.2_Files/RaFAH_v0.2.pl/download"
    curl -L --fail --retry 3 -o "${INSTALL_PREFIX}/src/RaFAH/RaFAH_0.2_README.md" "https://sourceforge.net/projects/rafah/files/RaFAH_v0.2_Files/RaFAH_0.2_README.md/download"
    chmod +x "${INSTALL_PREFIX}/src/RaFAH/RaFAH_v0.2.pl"
fi
if [[ "$INSTALL_DATABASES" -eq 1 && ! -f "${INSTALL_PREFIX}/src/RaFAH/.rafah_fetch_complete" ]]; then
    (cd "${INSTALL_PREFIX}/src/RaFAH" && "${INSTALL_PREFIX}/envs/rafah/bin/perl" RaFAH_v0.2.pl --fetch)
    touch "${INSTALL_PREFIX}/src/RaFAH/.rafah_fetch_complete"
fi

mkdir -p "${INSTALL_PREFIX}/examples"
cp "${PROJECT_ROOT}/examples/Bam35c_NC_005258.1.fasta" "${INSTALL_PREFIX}/examples/"

cp "${PROJECT_ROOT}/installer/wrappers/"* "${INSTALL_PREFIX}/bin/"
chmod +x "${INSTALL_PREFIX}/bin/"*
cp "${PROJECT_ROOT}/installer/activate.sh" "${INSTALL_PREFIX}/activate.sh"

if [[ "$INSTALL_DATABASES" -eq 1 ]]; then
    printf '%s\n' "Installing Pharokka database..."
    if [[ ! -f "${INSTALL_PREFIX}/databases/.pharokka.complete" ]]; then
        "${INSTALL_PREFIX}/bin/pharokka" install -o "${INSTALL_PREFIX}/databases/pharokka"
        touch "${INSTALL_PREFIX}/databases/.pharokka.complete"
    else
        printf '%s\n' "Pharokka database already marked complete."
    fi

    printf '%s\n' "Installing taxmyPHAGE database..."
    if [[ ! -f "${INSTALL_PREFIX}/databases/.taxmyphage.complete" ]]; then
        "${INSTALL_PREFIX}/bin/taxmyphage" install -db "${INSTALL_PREFIX}/databases/taxmyphage"
        for required_db in VMR.xlsx ICTV.msh M.pa Bacteriophage_genomes.fasta.nhr; do
            if [[ ! -s "${INSTALL_PREFIX}/databases/taxmyphage/${required_db}" ]]; then
                printf 'taxmyPHAGE database validation failed: missing %s\n' "$required_db" >&2
                exit 1
            fi
        done
        touch "${INSTALL_PREFIX}/databases/.taxmyphage.complete"
    else
        printf '%s\n' "taxmyPHAGE database already marked complete."
    fi
fi

printf '%s\n' "Running installation smoke checks..."
"${INSTALL_PREFIX}/bin/phagetriage" --version
"${INSTALL_PREFIX}/bin/pharokka" -h >/dev/null
"${INSTALL_PREFIX}/bin/Replidec" -h >/dev/null
"${INSTALL_PREFIX}/bin/taxmyphage" -h >/dev/null
"${INSTALL_PREFIX}/bin/viralcomplete" -h >/dev/null
"${INSTALL_PREFIX}/bin/RaFAH.py" -h >/dev/null

printf '\nInstallation complete.\n\n'
printf 'Activate it with:\n  source %q\n\n' "${INSTALL_PREFIX}/activate.sh"
printf 'Then verify it with:\n  %q doctor\n\n' "${INSTALL_PREFIX}/bin/phagetriage"
printf 'Run the included end-to-end demo with:\n  %q demo\n' "${INSTALL_PREFIX}/bin/phagetriage"
