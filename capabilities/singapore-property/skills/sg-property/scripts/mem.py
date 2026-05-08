#!/usr/bin/env python3
"""sgprop memory CRUD CLI.

Storage layout:
    $SGPROP_HOME (default ~/.config/sgprop)/
        profile.json
        holdings.json
        candidates.json
        clients/
            index.json
            <client-id>.json

Schema policy: lenient. Unknown fields are accepted with a warning on stderr.
Known-field type mismatches are rejected (exit 2).

Output: stdout is always JSON when exit code is 0. Stderr is human-readable
warnings or, on exit 2, a JSON error object.
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


# ---------- paths ----------

def home() -> Path:
    p = Path(os.environ.get("SGPROP_HOME") or Path.home() / ".config" / "sgprop")
    p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, 0o700)
    except OSError:
        pass
    return p


def file_path(name: str) -> Path:
    return home() / name


# ---------- IO helpers ----------

def load(name: str, default: Any) -> Any:
    p = file_path(name)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@contextlib.contextmanager
def locked_write(name: str):
    """Yield the current value, write back what the caller stores in `state['value']`.

    Atomic via tempfile + os.replace, exclusive via fcntl.flock on a sidecar
    lockfile (so the lock survives the rename).
    """
    p = file_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.with_suffix(p.suffix + ".lock")
    lock_fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        current: Any
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                current = json.load(f)
        else:
            current = None
        state = {"value": current}
        yield state
        # write
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(p.parent),
            prefix=f".{p.name}.",
            suffix=".tmp",
            delete=False,
        )
        try:
            json.dump(state["value"], tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.chmod(tmp.name, 0o600)
        os.replace(tmp.name, p)
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


# ---------- error helper ----------

def die(message: str, **fields: Any):
    payload = {"error": message, **fields}
    sys.stderr.write(json.dumps(payload) + "\n")
    sys.exit(2)


def warn(message: str, **fields: Any) -> None:
    payload = {"warning": message, **fields}
    sys.stderr.write(json.dumps(payload) + "\n")


def deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base) if base else {}
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def clear_path(obj, dotted: str) -> bool:
    """Delete a nested key. Returns True if removed, False if missing."""
    parts = dotted.split(".")
    cur = obj
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    last = parts[-1]
    if isinstance(cur, dict) and last in cur:
        del cur[last]
        return True
    return False


def parse_json_arg(raw: str, what: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"{what} must be valid JSON", detail=str(e))


# ---------- dispatch ----------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="mem.py",
        description="sgprop memory CRUD. Resources: profile, holdings, candidates, clients, notes.",
    )
    sub = parser.add_subparsers(dest="resource", required=True)

    # ----- profile -----
    profile = sub.add_parser("profile")
    p_sub = profile.add_subparsers(dest="verb", required=True)
    p_sub.add_parser("get")
    p_set = p_sub.add_parser("set")
    p_set.add_argument("--patch", required=True)
    p_clear = p_sub.add_parser("clear")
    p_clear.add_argument("--field", required=True)

    args = parser.parse_args(argv)

    if args.resource == "profile":
        return _profile(args)
    die(f"resource not implemented: {args.resource}")
    return 2


def _profile(args) -> int:
    if args.verb == "get":
        sys.stdout.write(json.dumps(load("profile.json", {}), ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "set":
        patch = parse_json_arg(args.patch, "--patch")
        if not isinstance(patch, dict):
            die("--patch must be a JSON object")
        with locked_write("profile.json") as state:
            current = state["value"] or {}
            state["value"] = deep_merge(current, patch)
        sys.stdout.write(json.dumps(state["value"], ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "clear":
        with locked_write("profile.json") as state:
            current = state["value"] or {}
            clear_path(current, args.field)
            state["value"] = current
        sys.stdout.write(json.dumps(state["value"], ensure_ascii=False, indent=2) + "\n")
        return 0

    die(f"unknown verb: {args.verb}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
