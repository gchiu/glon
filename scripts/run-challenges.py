#!/usr/bin/env python3
"""Run Glon challenge cases and write machine-readable results.

A challenge is a directory under challenges/ with cases.json and a source file.
Each case supplies a Glon expression call. The runner appends `print <call>` to
the challenge source, executes the native Glon CLI, and records actual stdout,
stderr, exit status, duration and the pinned interpreter commit.

Exit status:
  0  all cases passed
  1  a language failure or an unexpected result
  2  a harness failure (bad input, missing interpreter, process not started)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "interpreter.json"
DEFAULT_CHALLENGES = ROOT / "challenges"
DEFAULT_OUTPUT = ROOT / "results"


class HarnessError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path):
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot read {path}: {exc}") from exc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def safe_relpath(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise HarnessError(f"unsafe relative path: {value}")
    return path


def spec_bytes(spec: dict) -> bytes:
    if not isinstance(spec, dict):
        raise HarnessError("file spec is not an object")
    if "text" in spec:
        return str(spec["text"]).encode("utf-8")
    if "hex" in spec:
        try:
            return bytes.fromhex(str(spec["hex"]))
        except ValueError as exc:
            raise HarnessError(f"invalid hex in file spec: {exc}") from exc
    if "byte" in spec:
        try:
            b = int(spec["byte"])
            n = int(spec.get("count", 0))
        except (TypeError, ValueError) as exc:
            raise HarnessError(f"invalid byte/count in file spec: {exc}") from exc
        if not 0 <= b <= 255 or n < 0:
            raise HarnessError("byte/count out of range")
        prefix = spec_bytes({"text": spec["prefix_text"]}) if "prefix_text" in spec else b""
        suffix = spec_bytes({"text": spec["suffix_text"]}) if "suffix_text" in spec else b""
        return prefix + bytes([b]) * n + suffix
    raise HarnessError("file spec needs text, hex or byte/count")


def replace_bytes(spec: dict, initial: dict[str, bytes]) -> bytes:
    path = str(spec.get("path", ""))
    if path not in initial:
        raise HarnessError(f"expected_replace source is missing: {path}")
    if "old_text" in spec:
        old = str(spec["old_text"]).encode("utf-8")
    elif "old_hex" in spec:
        try:
            old = bytes.fromhex(str(spec["old_hex"]))
        except ValueError as exc:
            raise HarnessError(f"invalid old_hex: {exc}") from exc
    else:
        raise HarnessError("expected_replace needs old_text or old_hex")
    if "new_text" in spec:
        new = str(spec["new_text"]).encode("utf-8")
    elif "new_hex" in spec:
        try:
            new = bytes.fromhex(str(spec["new_hex"]))
        except ValueError as exc:
            raise HarnessError(f"invalid new_hex: {exc}") from exc
    else:
        new = b""
    return initial[path].replace(old, new, 1)

def write_case_files(work: Path, files, symlinks, hardlinks) -> dict[str, bytes]:
    initial = {}
    for spec in files or []:
        if not isinstance(spec, dict):
            raise HarnessError("files entry is not an object")
        path = safe_relpath(str(spec.get("path", "")))
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = spec_bytes(spec)
        target.write_bytes(data)
        initial[str(path)] = data
    for spec in symlinks or []:
        if not isinstance(spec, dict):
            raise HarnessError("symlinks entry is not an object")
        path = safe_relpath(str(spec.get("path", "")))
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(spec.get("target", "")), target)
    for spec in hardlinks or []:
        if not isinstance(spec, dict):
            raise HarnessError("hardlinks entry is not an object")
        path = safe_relpath(str(spec.get("path", "")))
        target = safe_relpath(str(spec.get("target", "")))
        link = work / path
        link.parent.mkdir(parents=True, exist_ok=True)
        os.link(work / target, link)
    return initial


def temp_files(work: Path) -> list[str]:
    found = []
    for p in work.rglob(".glon-tmp-*"):
        found.append(str(p.relative_to(work)))
    return found


def run_program(glon: Path, program: Path, timeout: float, args=(), cwd=None) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [str(glon), *map(str, args), str(program)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd if cwd is not None else program.parent),
        )
        duration = int((time.monotonic() - started) * 1000)
        return {
            "status": "completed",
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": duration,
        }
    except subprocess.TimeoutExpired as exc:
        duration = int((time.monotonic() - started) * 1000)
        return {
            "status": "timeout",
            "exit_code": None,
            "stdout": decode(exc.stdout),
            "stderr": decode(exc.stderr),
            "duration_ms": duration,
        }
    except OSError as exc:
        raise HarnessError(f"cannot execute {glon}: {exc}") from exc


def classify(case: dict, observed: dict, file_checks: list[dict] | None = None) -> str:
    if observed["status"] == "timeout":
        return "timeout"
    expected_exit = int(case.get("expected_exit", 0))
    expected_stdout = case.get("expected_stdout", "")
    actual_exit = observed["exit_code"]
    if actual_exit != expected_exit:
        if actual_exit != 0 and expected_exit == 0:
            return "language_error"
        return "exit_mismatch"
    if observed["stdout"] != expected_stdout:
        return "output_mismatch"
    needle = case.get("expected_stderr_contains")
    if needle and str(needle) not in (observed.get("stderr") or ""):
        return "stderr_mismatch"
    for check in file_checks or []:
        if check.get("status") != "pass":
            return check.get("status", "file_mismatch")
    return "pass"


def program_text(library_prefix: str, source: str, call: str, print_value: bool) -> str:
    statement = ("print " if print_value else "") + call.strip()
    return library_prefix + source.rstrip() + "\n" + statement + "\n"


def file_checks_for_case(case: dict, work: Path, initial: dict[str, bytes]) -> list[dict]:
    checks = []
    expected_files = case.get("expected_files", [])
    if isinstance(expected_files, dict):
        expected_files = [expected_files]
    for spec in expected_files or []:
        path = str(spec.get("path", ""))
        expected = spec_bytes(spec)
        target = work / safe_relpath(path)
        actual = target.read_bytes() if target.is_file() else None
        checks.append({
            "path": path,
            "kind": "file",
            "expected_size": len(expected),
            "actual_size": len(actual) if actual is not None else None,
            "status": "pass" if actual == expected else "file_mismatch",
        })

    expected_replace = case.get("expected_replace")
    if expected_replace:
        items = expected_replace if isinstance(expected_replace, list) else [expected_replace]
        for spec in items:
            path = str(spec.get("path", ""))
            expected = replace_bytes(spec, initial)
            target = work / safe_relpath(path)
            actual = target.read_bytes() if target.is_file() else None
            checks.append({
                "path": path,
                "kind": "replace",
                "expected_size": len(expected),
                "actual_size": len(actual) if actual is not None else None,
                "status": "pass" if actual == expected else "file_mismatch",
            })

    for rel in case.get("expected_absent", []) or []:
        path = str(rel)
        target = work / safe_relpath(path)
        checks.append({
            "path": path,
            "kind": "absent",
            "status": "pass" if not target.exists() else "file_present",
        })

    for spec in case.get("expected_symlinks", []) or []:
        path = str(spec.get("path", ""))
        target = str(spec.get("target", ""))
        link = work / safe_relpath(path)
        ok = link.is_symlink() and os.readlink(link) == target
        checks.append({
            "path": path,
            "kind": "symlink",
            "target": target,
            "status": "pass" if ok else "symlink_mismatch",
        })

    if case.get("expect_no_temp", True):
        leftovers = temp_files(work)
        checks.append({
            "path": ".",
            "kind": "temp_cleanup",
            "leftovers": leftovers,
            "status": "pass" if not leftovers else "temp_left",
        })
    return checks


def run_case(glon: Path, source: str, case: dict, timeout: float, tmp: Path,
             library_prefix: str = "", meta: dict | None = None) -> dict:
    meta = meta or {}
    if not isinstance(case, dict):
        raise HarnessError("case entry is not an object")
    case_id = str(case.get("id", "unnamed"))
    call = case.get("call")
    if not isinstance(call, str) or not call.strip():
        raise HarnessError(f"case {case_id} has no call expression")
    if "expected_stdout" not in case:
        raise HarnessError(f"case {case_id} has no expected_stdout")

    is_file = bool(meta.get("requires_file_module")) or any(
        key in case for key in ("files", "expected_files", "expected_replace",
                                "expected_absent", "expected_symlinks")
    ) or bool(case.get("flags"))
    safe_id = case_id.replace("/", "_")
    if is_file:
        case_root = tmp / safe_id
        work = case_root / "work"
        work.mkdir(parents=True, exist_ok=True)
        initial = write_case_files(
            work,
            case.get("files", meta.get("files", [])),
            case.get("symlinks", meta.get("symlinks", [])),
            case.get("hardlinks", meta.get("hardlinks", [])),
        )
        program = case_root / "run.glon"
        grants = case.get("grants", meta.get("io_grants", ["read", "write"]))
        args = ["--io-root", str(work)]
        if "read" in grants:
            args.append("--allow-file-read")
        if "write" in grants:
            args.append("--allow-file-write")
        args += [str(x) for x in case.get("flags", [])]
        cwd = case_root
    else:
        work = None
        initial = {}
        program = tmp / (safe_id + ".glon")
        args = []
        cwd = tmp

    program.write_text(
        program_text(library_prefix, source, call, bool(case.get("print", True))),
        encoding="utf-8",
    )
    case_timeout = float(case.get("timeout", timeout))
    observed = run_program(glon, program, case_timeout, args, cwd)
    file_checks = file_checks_for_case(case, work, initial) if is_file else []
    status = classify(case, observed, file_checks)
    result = {
        "id": case_id,
        "call": call,
        "reference": case.get("reference", ""),
        "expected_exit": int(case.get("expected_exit", 0)),
        "expected_stdout": case.get("expected_stdout", ""),
        "actual_exit": observed["exit_code"],
        "actual_stdout": observed["stdout"],
        "actual_stderr": observed["stderr"],
        "duration_ms": observed["duration_ms"],
        "status": status,
    }
    if file_checks:
        result["file_checks"] = file_checks
    return result

def run_probe(glon: Path, source: str, probe: dict, timeout: float, tmp: Path, library_prefix: str = "") -> dict:
    probe_id = str(probe.get("id", "probe"))
    call = probe.get("call")
    if not isinstance(call, str) or not call.strip():
        raise HarnessError(f"probe {probe_id} has no call expression")
    program = tmp / ("probe-" + probe_id.replace("/", "_") + ".glon")
    program.write_text(
        program_text(library_prefix, source, call, bool(probe.get("print", True))),
        encoding="utf-8",
    )
    observed = run_program(glon, program, timeout)
    return {
        "id": probe_id,
        "call": call,
        "note": probe.get("note", ""),
        "documented_observation": probe.get("observed", ""),
        "actual_exit": observed["exit_code"],
        "actual_stdout": observed["stdout"],
        "actual_stderr": observed["stderr"],
        "duration_ms": observed["duration_ms"],
        "status": observed["status"],
    }


def challenge_result(glon: Path, challenge_dir: Path, timeout: float, run_probes: bool, config: dict, interpreter_sha: str) -> tuple[dict, bool, bool]:
    cases_path = challenge_dir / "cases.json"
    try:
        meta = read_json(cases_path)
        if not isinstance(meta, dict):
            raise HarnessError(f"{cases_path}: top level must be an object")
        source_name = meta.get("source")
        if not isinstance(source_name, str):
            raise HarnessError(f"{cases_path}: missing source filename")
        source_path = challenge_dir / source_name
        source = source_path.read_text(encoding="utf-8")
        cases = meta.get("cases")
        if not isinstance(cases, list) or not cases:
            raise HarnessError(f"{cases_path}: missing non-empty cases list")
        libraries = meta.get("libraries", []) or []
        if not isinstance(libraries, list):
            raise HarnessError(f"{cases_path}: libraries must be a list")
        library_prefix = ""
        for library in libraries:
            if not isinstance(library, str):
                raise HarnessError(f"{cases_path}: library entry is not a string")
            library_path = challenge_dir / library
            library_text = library_path.read_text(encoding="utf-8")
            library_prefix += "do " + library_text.strip() + "\n"
        reference = meta.get("reference_implementation")
        if reference is not None:
            if not isinstance(reference, dict):
                raise HarnessError(f"{cases_path}: reference_implementation must be an object")
            ref_source = reference.get("source")
            if not isinstance(ref_source, str):
                raise HarnessError(f"{cases_path}: reference_implementation.source is missing")
            ref_path = challenge_dir / ref_source
            reference = dict(reference)
            reference["source_sha256"] = sha256(ref_path)
        comparison = meta.get("implementation_comparison")
        if comparison is not None and not isinstance(comparison, dict):
            raise HarnessError(f"{cases_path}: implementation_comparison must be an object")
    except (OSError, HarnessError) as exc:
        name = challenge_dir.name
        return ({
            "schema": 1,
            "challenge": name,
            "generated_at": utc_now(),
            "interpreter": {
                "commit": config.get("commit"),
                "repository": config.get("repository"),
                "sha256": interpreter_sha,
            },
            "all_passed": False,
            "harness_error": str(exc),
            "summary": {"total": 0, "passed": 0, "failed": 0, "timeouts": 0, "harness_errors": 1},
            "cases": [],
            "resource_probes": [],
            "known_limitations": [],
            "implementation_status": "harness_error",
            "blocker": "",
            "host_dependency": "",
            "reference_implementation": None,
            "implementation_comparison": None,
        }, False, True)

    results = []
    harness_error = False
    with tempfile.TemporaryDirectory(prefix=f"glon-{challenge_dir.name}-") as td:
        tmp = Path(td)
        for case in cases:
            try:
                results.append(run_case(glon, source, case, timeout, tmp, library_prefix, meta))
            except HarnessError as exc:
                harness_error = True
                results.append({
                    "id": str(case.get("id", "unnamed")) if isinstance(case, dict) else "unnamed",
                    "status": "harness_error",
                    "error": str(exc),
                })
        probes = []
        if run_probes:
            for probe in meta.get("resource_probes", []) or []:
                try:
                    probes.append(run_probe(glon, source, probe, timeout, tmp, library_prefix))
                except HarnessError as exc:
                    harness_error = True
                    probes.append({"id": str(probe.get("id", "probe")), "status": "harness_error", "error": str(exc)})

    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") not in ("pass",))
    timeouts = sum(1 for r in results if r.get("status") == "timeout")
    result = {
        "schema": 1,
        "challenge": meta.get("challenge", challenge_dir.name),
        "title": meta.get("title", challenge_dir.name),
        "entry": meta.get("entry"),
        "source": source_name,
        "domain": meta.get("domain", ""),
        "description": meta.get("description", ""),
        "attribution": meta.get("attribution", ""),
        "reference": meta.get("reference", ""),
        "generated_at": utc_now(),
        "interpreter": {
            "repository": config.get("repository"),
            "commit": config.get("commit"),
            "sha256": interpreter_sha,
        },
        "all_passed": (not harness_error and failed == 0),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "timeouts": timeouts,
            "harness_errors": sum(1 for r in results if r.get("status") == "harness_error"),
        },
        "implementation_status": meta.get("implementation_status", "verified"),
        "requires_file_module": bool(meta.get("requires_file_module")),
        "source_layer": meta.get("source_layer", "implementation"),
        "history": meta.get("history", []),
        "performance": meta.get("performance"),
        "blocker": meta.get("blocker", ""),
        "host_dependency": meta.get("host_dependency", ""),
        "libraries": meta.get("libraries", []),
        "reference_implementation": reference,
        "implementation_comparison": comparison,
        "cases": results,
        "resource_probes": probes,
        "known_limitations": meta.get("known_limitations", []),
    }
    return result, result["all_passed"], harness_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glon", required=True, help="path to the native glon executable")
    parser.add_argument("--challenges", type=Path, default=DEFAULT_CHALLENGES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--challenge", action="append", default=None, help="run only this challenge (repeatable)")
    parser.add_argument("--timeout", type=float, default=10.0, help="per-case timeout in seconds")
    parser.add_argument("--run-probes", action="store_true", help="execute resource probes and record actual observations")
    args = parser.parse_args()

    glon = Path(args.glon).resolve()
    if not glon.is_file() or not os.access(glon, os.X_OK):
        print(f"run-challenges: harness error: not an executable: {glon}", file=sys.stderr)
        return 2
    try:
        config = read_json(args.config)
        config_sha = sha256(glon)
    except (HarnessError, OSError) as exc:
        print(f"run-challenges: harness error: {exc}", file=sys.stderr)
        return 2

    selected = []
    if not args.challenges.is_dir():
        print(f"run-challenges: harness error: missing challenge directory: {args.challenges}", file=sys.stderr)
        return 2
    wanted = set(args.challenge or [])
    for child in sorted(args.challenges.iterdir()):
        if not child.is_dir() or not (child / "cases.json").is_file():
            continue
        if wanted and child.name not in wanted:
            continue
        selected.append(child)
    if not selected:
        print("run-challenges: harness error: no challenges selected", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    any_failure = False
    any_harness = False
    for child in selected:
        result, passed, harness = challenge_result(glon, child, args.timeout, args.run_probes, config, config_sha)
        out = args.output / (child.name + ".json")
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary = result["summary"]
        print(f"{'PASS' if passed else 'FAIL'} {child.name}: "
              f"{summary['passed']}/{summary['total']} passed, "
              f"{summary['failed']} failed, {summary['timeouts']} timed out"
              + (f", harness error: {result.get('harness_error')}" if result.get("harness_error") else ""))
        if not passed:
            any_failure = True
            for case in result.get("cases", []):
                if case.get("status") != "pass":
                    print(f"  {case.get('id')}: {case.get('status')} "
                          f"expected={case.get('expected_stdout')!r} actual={case.get('actual_stdout')!r} "
                          f"exit={case.get('actual_exit')} stderr={(case.get('actual_stderr') or '').strip()[:160]!r}")
        any_harness = any_harness or harness
    if any_harness:
        return 2
    return 1 if any_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
