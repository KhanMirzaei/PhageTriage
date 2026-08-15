# Contributing

Contributions are welcome through GitHub issues and pull requests.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

## Requirements for changes

- Add or update tests for behavior changes.
- Preserve evidence rows and upstream file paths in parsed findings.
- Do not convert “not detected” into a claim that a gene or property is absent.
- Do not weaken an `EXCLUDE` decision by averaging it with favorable evidence.
- Update `README.md` and `CHANGELOG.md` for user-visible changes.
- Keep external tool versions and database versions visible in run logs.

PhageTriage is research software. Contributions must not present computational predictions as clinical safety or efficacy determinations.

