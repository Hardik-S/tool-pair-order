"""Independent installed-package and console-script acceptance probe."""

import importlib.metadata
from pathlib import Path
import subprocess
import sysconfig
import sys
import tempfile


def main():
    import tool_pair_order

    assert importlib.metadata.version("tool-pair-order") == "0.1.0"
    origin = Path(tool_pair_order.__file__).resolve()
    repository = Path(__file__).resolve().parent
    assert (repository / "src") not in origin.parents, f"package imported from source tree: {origin}"
    scripts = Path(sysconfig.get_path("scripts"))
    command_path = scripts / ("tool-pair-order.exe" if sysconfig.get_platform().startswith("win")
                              else "tool-pair-order")
    assert command_path.is_file(), f"installed console script is missing from {scripts}"
    command = str(command_path)
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)
        valid = source / "valid.jsonl"
        valid.write_text('{"id":"c","kind":"call","call_id":"x"}\n'
                         '{"id":"r","kind":"result","call_id":"x"}\n', encoding="utf-8")
        issue = source / "issue.jsonl"
        issue.write_text('{"id":"c","kind":"call","call_id":"x"}\n', encoding="utf-8")
        invalid = source / "invalid.jsonl"
        invalid.write_text("{\n", encoding="utf-8")
        checks = [
            ([command, str(valid)], 0, b'{"status":"valid","record_count":2,"issue_lines":[]}\n'),
            ([command, str(issue)], 1, b'{"status":"pair_issues","record_count":1,"issue_lines":[1]}\n'),
            ([command, str(invalid)], 2, b'{"status":"invalid_input"}\n'),
            ([command, "--help"], 0, None),
        ]
        for args, code, stdout in checks:
            result = subprocess.run(args, capture_output=True)
            assert result.returncode == code, (args[1:], result.returncode)
            assert result.stderr == b"", (args[1:], result.stderr)
            if stdout is not None:
                assert result.stdout == stdout, (args[1:], result.stdout)
            elif b"usage: tool-pair-order EVENTS.jsonl" not in result.stdout:
                raise AssertionError("help text missing")
    print(f"installed 0.1.0 acceptance passed ({origin})")


if __name__ == "__main__":
    main()
