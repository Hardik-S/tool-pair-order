import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tool_pair_order.cli import InvalidInput, check_bytes


def line(event_id, kind, call_id):
    return json.dumps({"id": event_id, "kind": kind, "call_id": call_id},
                      ensure_ascii=True, separators=(",", ":"))


def run_data(data, *args):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "input.jsonl"
        path.write_bytes(data)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
        return subprocess.run([sys.executable, "-m", "tool_pair_order.cli", *args, str(path)],
                              capture_output=True, env=env)


class PairGrammarTests(unittest.TestCase):
    def test_empty_and_valid_interleaved_pairs(self):
        self.assertEqual(check_bytes(b"") , {"status": "valid", "record_count": 0, "issue_lines": []})
        data = "\n".join([line("a", "call", "x"), line("b", "call", "y"),
                           line("c", "result", "x"), line("d", "result", "y")]).encode()
        self.assertEqual(check_bytes(data)["status"], "valid")

    def test_orphans_and_missing_rows(self):
        data = "\n".join([line("a", "call", "x"), line("b", "result", "y")]).encode()
        self.assertEqual(check_bytes(data)["issue_lines"], [1, 2])

    def test_result_before_call_reports_both_rows(self):
        data = "\n".join([line("r", "result", "x"), line("c", "call", "x")]).encode()
        self.assertEqual(check_bytes(data)["issue_lines"], [1, 2])

    def test_duplicate_pair_kind_and_event_id_are_invalid(self):
        for data in (
            (line("a", "call", "x") + "\n" + line("b", "call", "x")).encode(),
            (line("a", "call", "x") + "\n" + line("a", "result", "y")).encode(),
        ):
            with self.assertRaises(InvalidInput):
                check_bytes(data)

    def test_unicode_exactness_and_newlines(self):
        a = line("é", "call", "α")
        b = line("e\u0301", "result", "α")
        self.assertEqual(check_bytes((a + "\r\n" + b + "\r\n").encode())["status"], "valid")
        with self.assertRaises(InvalidInput):
            check_bytes((a + "\u2028" + b).encode())

    def test_strict_json_inputs(self):
        bad = [b"\xff", b"\n", b"{}", b'{"id":"a","id":"b","kind":"call","call_id":"x"}',
               b'{"id":"a","kind":"call","call_id":"x","extra":1}',
               b'{"id":"a","kind":"call","call_id":"x"}\n\n',
               b'{"id":"\\ud800","kind":"call","call_id":"x"}',
               b'{"id":"a","kind":"call","call_id":"x","v":NaN}',
               b'{"id":"a","kind":"call","call_id":"x","v":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"]
        for data in bad:
            with self.subTest(data=data[:40]), self.assertRaises(InvalidInput):
                check_bytes(data)

    def test_cli_exit_contract_and_private_diagnostics(self):
        valid = run_data((line("c", "call", "secret-id") + "\n" + line("r", "result", "secret-id")).encode())
        self.assertEqual((valid.returncode, valid.stdout, valid.stderr),
                         (0, b'{"status":"valid","record_count":2,"issue_lines":[]}\n', b""))
        issue = run_data(line("c", "call", "secret-id").encode())
        self.assertEqual((issue.returncode, issue.stdout), (1, b'{"status":"pair_issues","record_count":1,"issue_lines":[1]}\n'))
        invalid = run_data(b"not-json", "--private-argument")
        self.assertEqual((invalid.returncode, invalid.stdout, invalid.stderr),
                         (2, b'{"status":"invalid_input"}\n', b""))
        self.assertNotIn(b"secret-id", issue.stdout + issue.stderr)

    def test_argv_and_unreadable_file_share_fixed_invalid_response(self):
        expected = (2, b'{"status":"invalid_input"}\n', b"")
        for args in ([], ["one", "two"], ["--private-secret"],
                     ["missing-private-path-7821.jsonl"]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, "-m", "tool_pair_order.cli", *args],
                                        capture_output=True)
                self.assertEqual((result.returncode, result.stdout, result.stderr), expected)

    def test_help(self):
        proc = subprocess.run([sys.executable, "-m", "tool_pair_order.cli", "--help"], capture_output=True)
        self.assertEqual((proc.returncode, proc.stderr), (0, b""))


if __name__ == "__main__":
    unittest.main()
