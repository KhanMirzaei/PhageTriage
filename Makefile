.PHONY: test syntax dry-run

test:
	PYTHONPATH=src python -m unittest discover -s tests -v

syntax:
	bash -n install_all.sh
	for file in installer/wrappers/*; do bash -n "$$file"; done
	bash -n phagetriage.sh
	PYTHONPATH=src python -m compileall -q src tests

dry-run:
	mkdir -p /tmp/phagetriage_dry_run
	PYTHONPATH=src python -m phagetriage run --input examples/phages.fasta --output /tmp/phagetriage_dry_run --threads 2 --dry-run
