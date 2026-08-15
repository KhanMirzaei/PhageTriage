#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${PHAGETRIAGE_PREFIX:-${HOME}/PhageTriageBundle}"

usage() {
    cat <<'EOF'
PhageTriage easy launcher

Usage:
  bash phagetriage.sh install [installer options]
  bash phagetriage.sh uninstall [--yes] [--prefix PATH]
  bash phagetriage.sh doctor
  bash phagetriage.sh demo [--output PATH] [--threads N]
  bash phagetriage.sh run -i PHAGES.fasta -o RESULTS [--hosts HOST_FASTA_DIR] [options]
  bash phagetriage.sh update [installer options]

The default runtime is $HOME/PhageTriageBundle. Override it with:
  PHAGETRIAGE_PREFIX=/path/without_spaces/PhageTriageBundle bash phagetriage.sh install

Output, host, database, and runtime paths must not contain spaces.
EOF
}

require_install() {
    if [[ ! -x "${INSTALL_ROOT}/bin/phagetriage" ]]; then
        printf 'PhageTriage is not installed at %s.\n' "${INSTALL_ROOT}" >&2
        printf 'Run: bash %q install\n' "${PROJECT_ROOT}/phagetriage.sh" >&2
        exit 1
    fi
}

command_name="${1:-help}"
if [[ $# -gt 0 ]]; then
    shift
fi

case "${command_name}" in
    install|update)
        exec bash "${PROJECT_ROOT}/install_all.sh" --prefix "${INSTALL_ROOT}" "$@"
        ;;
    uninstall)
        exec bash "${PROJECT_ROOT}/uninstall.sh" --prefix "${INSTALL_ROOT}" "$@"
        ;;
    doctor)
        require_install
        exec "${INSTALL_ROOT}/bin/phagetriage" doctor "$@"
        ;;
    demo)
        require_install
        exec "${INSTALL_ROOT}/bin/phagetriage" demo "$@"
        ;;
    run)
        require_install
        exec "${INSTALL_ROOT}/bin/phagetriage" run "$@"
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        printf 'Unknown command: %s\n\n' "${command_name}" >&2
        usage >&2
        exit 2
        ;;
esac
