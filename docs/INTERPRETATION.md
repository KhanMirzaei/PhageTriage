# Interpreting PhageTriage results

PhageTriage is a research triage workflow, not a clinical decision system.

## Verdicts

- `EXCLUDE`: a configured hard genomic exclusion was detected, such as a non-lytic replication-cycle prediction or a CARD/VFDB hit.
- `REVIEW`: required evidence is missing, uncertain or requires manual confirmation.
- `CANDIDATE_FOR_WET_LAB_REVIEW`: configured computational gates passed; experimental validation remains mandatory.

## Important language

An empty database hit table means “not detected using this database version and threshold.” It does not prove biological absence. Unknown or incorrectly annotated proteins can conceal relevant functions.

## Required follow-up outside this workflow

- Read-backed genome closure and termini determination.
- Experimental lysogeny and generalized-transduction assessment.
- Productive host-range and efficiency-of-plating testing.
- Phage-resistance and biofilm studies where relevant.
- Sterility, endotoxin, residual host DNA/protein and stability testing.
- Appropriate nonclinical, clinical and regulatory review.

