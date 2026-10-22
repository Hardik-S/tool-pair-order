# Tool Pair Order

Tool Pair Order checks ordering in a **normalized synthetic event-pair format**. It is an offline Python 3.10+ command-line utility with no runtime dependencies.

It is not an MCP validator and does not connect to providers, execute tools, or model tool error results. Its output makes no claim about execution success, safety, security, quality, or novelty.

## Install and run

Create a fresh environment, install the package noneditably, then run the installed command:

```console
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux (use this instead of the Windows activation command):
source .venv/bin/activate
python -m pip install .
tool-pair-order examples/interleaved.jsonl
```

The build uses `setuptools` as its PEP 517 backend. If your environment disallows build isolation, install the backend explicitly (`python -m pip install setuptools`) before `python -m pip install --no-build-isolation .`. Runtime execution uses only the Python standard library.

The valid example prints `{"status":"valid","record_count":4,"issue_lines":[]}` and exits 0. For a result-before-call example:

```console
tool-pair-order examples/result-before-call.jsonl
```

It prints `{"status":"pair_issues","record_count":2,"issue_lines":[1,2]}` and exits 1. Invalid input prints `{"status":"invalid_input"}` and exits 2. Help is available with `tool-pair-order --help`.

## Input grammar

Each physical JSONL row must be one JSON object with exactly these fields:

```json
{"id":"event-1","kind":"call","call_id":"call-1"}
```

`id` and `call_id` must be nonempty strings. `id` must be unique across the file. `kind` is exactly `call` or `result`. Each exact `call_id` may occur at most once for either kind. Matching uses exact Unicode code points without normalization. Independent pairs may interleave.

A pair is properly ordered when both rows exist and its call row precedes its result row. An unmatched call identifies its call row; an orphan result identifies its result row; a result before its call identifies both rows. Issue rows are sorted and unique. An empty file is valid with zero records.

Input must be strict UTF-8. Physical line endings may be LF, CR, or CRLF, with an optional final terminator. Blank rows, duplicate JSON object keys, non-finite JSON numbers, invalid UTF-8, surrogate code points, deeply nested JSON that exceeds the decoder's safe limit, malformed JSON, wrong field sets, and wrong types invalidate the entire file. Unicode line-separator characters are not JSONL delimiters. The file is validated fully before a result is written.

Invalid input, unreadable files, and unsupported or extra command-line arguments all produce the same fixed output and no diagnostic details. The command never prints input IDs, kinds, call IDs, paths, source content, hashes, or exception text.

## Development

Run the full test suite after installing the package noneditably:

```console
python -m pip install .
python -m unittest discover -s tests -v
python acceptance.py
```

CI covers Ubuntu and Windows with Python 3.10 and 3.13.
