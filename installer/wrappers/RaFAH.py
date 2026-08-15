#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
export PATH="$ROOT/envs/rafah/bin:$PATH"
INPUT=""
OUTPUT=""
THREADS=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input) INPUT="$2"; shift 2;;
        -o|--output) OUTPUT="$2"; shift 2;;
        -t|--threads) THREADS="$2"; shift 2;;
        -h|--help)
            printf '%s\n' 'Usage: RaFAH.py -i INPUT_FASTA_DIRECTORY -o OUTPUT_DIRECTORY [-t THREADS]'
            exit 0;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 2;;
    esac
done
[[ -n "$INPUT" && -n "$OUTPUT" ]] || { printf '%s\n' 'RaFAH requires -i INPUT and -o OUTPUT.' >&2; exit 2; }
INPUT="${INPUT%/}/"
mkdir -p "$OUTPUT"
exec bash -c 'cd "$1" && "$2" "$3/RaFAH_v0.2.pl" --predict --genomes_dir "$4" --extension .fasta --file_prefix RaFAH --threads "$5" --valid_ogs_file "$3/HP_Ranger_Model_3_Valid_Cols.txt" --hmmer_db_file_name "$3/HP_Ranger_Model_3_Filtered_0.9_Valids.hmm" --r_script_predict_file_name "$3/RaFAH_Predict_Host.R" --r_model_file_name "$3/MMSeqs_Clusters_Ranger_Model_1+2+3_Clean.RData"' _ "$OUTPUT" "$ROOT/envs/rafah/bin/perl" "$ROOT/src/RaFAH" "$INPUT" "$THREADS"
