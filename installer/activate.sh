#!/usr/bin/env bash
PHAGETRIAGE_INSTALL_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PHAGETRIAGE_INSTALL_ROOT
export PATH="${PHAGETRIAGE_INSTALL_ROOT}/bin:${PATH}"
export PHAGETRIAGE_PHAROKKA_DB="${PHAGETRIAGE_INSTALL_ROOT}/databases/pharokka"
export PHAGETRIAGE_TAXMYPHAGE_DB="${PHAGETRIAGE_INSTALL_ROOT}/databases/taxmyphage"

