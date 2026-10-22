"""Command line entry point for the normalized event-pair checker."""

import json
import sys
from pathlib import Path
from typing import Any


class InvalidInput(Exception):
    """Input cannot be interpreted under the documented event grammar."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise InvalidInput


def _has_surrogate(value: Any) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                return True
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


def check_bytes(data: bytes) -> dict[str, Any]:
    try:
        source = data.decode("utf-8", errors="strict")
        # str.splitlines treats Unicode separators as delimiters, so delimit only
        # the three physical newline encodings accepted by JSONL here.
        lines = [] if source == "" else __import__("re").split(r"\r\n|\r|\n", source)
        if lines and lines[-1] == "" and source.endswith(("\r", "\n")):
            lines.pop()
        events: list[tuple[int, dict[str, Any]]] = []
        seen_ids: set[str] = set()
        for row, line in enumerate(lines, 1):
            if not line:
                raise InvalidInput
            obj = json.loads(line, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
            if not isinstance(obj, dict) or set(obj) != {"id", "kind", "call_id"}:
                raise InvalidInput
            if _has_surrogate(obj):
                raise InvalidInput
            event_id, kind, call_id = obj["id"], obj["kind"], obj["call_id"]
            if (not isinstance(event_id, str) or not event_id or
                    not isinstance(call_id, str) or not call_id or
                    kind not in ("call", "result") or not isinstance(kind, str) or
                    event_id in seen_ids):
                raise InvalidInput
            seen_ids.add(event_id)
            events.append((row, obj))

        pairs: dict[str, dict[str, int]] = {}
        for row, event in events:
            pair = pairs.setdefault(event["call_id"], {})
            kind = event["kind"]
            if kind in pair:
                raise InvalidInput
            pair[kind] = row

        issues: set[int] = set()
        for pair in pairs.values():
            call_row, result_row = pair.get("call"), pair.get("result")
            if call_row is None:
                issues.add(result_row)  # orphan result
            elif result_row is None:
                issues.add(call_row)  # unmatched call
            elif call_row > result_row:
                issues.update((call_row, result_row))
        return {"status": "pair_issues" if issues else "valid",
                "record_count": len(events), "issue_lines": sorted(issues)}
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError,
            InvalidInput, ValueError, TypeError, OverflowError):
        raise InvalidInput from None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["-h"] or args == ["--help"]:
        sys.stdout.buffer.write(b"usage: tool-pair-order EVENTS.jsonl\n")
        sys.stdout.buffer.write(b"Check ordering in normalized synthetic tool event pairs.\n")
        return 0
    if len(args) != 1 or args[0].startswith("-"):
        sys.stdout.buffer.write(b'{"status":"invalid_input"}\n')
        return 2
    try:
        result = check_bytes(Path(args[0]).read_bytes())
    except (OSError, InvalidInput):
        sys.stdout.buffer.write(b'{"status":"invalid_input"}\n')
        return 2
    sys.stdout.buffer.write((json.dumps(result, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii"))
    return 1 if result["status"] == "pair_issues" else 0


if __name__ == "__main__":
    raise SystemExit(main())
