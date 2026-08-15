#!/usr/bin/env bash
set -euo pipefail

INSTALL_PREFIX="${PHAGETRIAGE_PREFIX:-${HOME}/PhageTriageBundle}"
ASSUME_YES=0

usage() {
    cat <<'EOF'
Usage: bash uninstall.sh [--prefix PATH] [--yes]

Removes only the self-contained PhageTriage installation at PATH.
The default is $HOME/PhageTriageBundle. Analysis results stored inside that
directory are also removed, so copy any results you want to retain first.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            [[ $# -ge 2 ]] || { printf '%s\n' "--prefix requires a path" >&2; exit 2; }
            INSTALL_PREFIX="$2"
            shift 2
            ;;
        --yes|-y)
            ASSUME_YES=1
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

if [[ ! -e "${INSTALL_PREFIX}" ]]; then
    printf 'PhageTriage is not installed at %s. Nothing to remove.\n' "${INSTALL_PREFIX}"
    exit 0
fi

INSTALL_PREFIX="$(cd -- "${INSTALL_PREFIX}" && pwd -P)"

if [[ "${INSTALL_PREFIX}" == "/" || "${INSTALL_PREFIX}" == "${HOME}" ]]; then
    printf 'Refusing unsafe uninstall target: %s\n' "${INSTALL_PREFIX}" >&2
    exit 2
fi

if [[ ! -f "${INSTALL_PREFIX}/.phagetriage-installation" ]]; then
    if [[ ! -x "${INSTALL_PREFIX}/bin/phagetriage" || \
          ! -d "${INSTALL_PREFIX}/envs/phagetriage" || \
          ! -f "${INSTALL_PREFIX}/activate.sh" ]]; then
        printf 'Refusing to remove %s: it is not recognizable as a PhageTriage installation.\n' "${INSTALL_PREFIX}" >&2
        exit 2
    fi
fi

printf 'PhageTriage installation to remove:\n  %s\n' "${INSTALL_PREFIX}"
printf '%s\n' "This includes bundled environments, databases, and results stored inside it."

if [[ "${ASSUME_YES}" -ne 1 ]]; then
    printf 'Type REMOVE to continue: '
    read -r confirmation
    if [[ "${confirmation}" != "REMOVE" ]]; then
        printf '%s\n' "Uninstall cancelled."
        exit 0
    fi
fi

rm -rf -- "${INSTALL_PREFIX}"
printf 'Removed PhageTriage from %s\n' "${INSTALL_PREFIX}"
