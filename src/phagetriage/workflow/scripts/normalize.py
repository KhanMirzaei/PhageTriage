from pathlib import Path

from phagetriage.fasta import infer_topology, read_fasta, write_fasta

records = read_fasta(Path(snakemake.input[0]))
for record in records:
    infer_topology(record, snakemake.params.topology, int(snakemake.params.min_overlap), int(snakemake.params.max_overlap))
write_fasta(records, Path(snakemake.output.combined))
for record in records:
    write_fasta([record], Path(snakemake.output.combined).parent / f"{record.sample}.fasta")
