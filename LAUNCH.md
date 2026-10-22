# Launch checklist

1. Create a clean virtual environment and run `python -m pip install .` (noneditable).
2. Run `python acceptance.py`; it verifies distribution version, installed import location, sysconfig console-script path, and exit/output behavior for valid, issue, invalid, and help cases.
3. Run `python -m unittest discover -s tests -v`; require zero failures and zero skips.
4. Inspect the GitHub Actions matrix for Ubuntu and Windows on Python 3.10 and 3.13.
5. Review the synthetic-only scope and fixed-output privacy contract before publishing a release archive.

This checklist does not certify MCP compatibility, live execution behavior, tool success, safety, security, quality, or novelty.
