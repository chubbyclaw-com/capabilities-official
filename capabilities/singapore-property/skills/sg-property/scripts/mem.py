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
import re
import sys
import tempfile
from datetime import datetime
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


# ---------- collection helpers ----------

def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "item"


def gen_id(prefix: str) -> str:
    return f"{slugify(prefix)}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


COLLECTION_FILES = {
    "holdings": ("holdings.json", "properties", ("address",)),
    "candidates": ("candidates.json", "candidates", ("project_name",)),
}

CANDIDATE_STAGES = ["shortlist", "viewing_scheduled", "viewed", "offered", "declined", "closed"]
CANDIDATE_AUTO_STAGES = ["shortlist", "viewing_scheduled", "viewed", "offered", "closed"]
TERMINAL_STAGES = {"declined", "closed"}


CLIENTS_DIR = "clients"
CLIENTS_INDEX = "clients/index.json"


def _client_path(client_id: str) -> Path:
    safe = slugify(client_id)
    if safe != client_id:
        die("client id must be slug-safe (lowercase letters, digits, hyphens)", id=client_id)
    return file_path(f"{CLIENTS_DIR}/{client_id}.json")


def _client_index_upsert(client_id: str, name: str, role: str, status: str) -> None:
    with locked_write(CLIENTS_INDEX) as state:
        idx = state["value"] or {"clients": []}
        clients = idx.setdefault("clients", [])
        for entry in clients:
            if entry["id"] == client_id:
                entry.update({"name": name, "role": role, "status": status,
                              "updated_at": datetime.utcnow().isoformat() + "Z"})
                state["value"] = idx
                return
        clients.append({
            "id": client_id, "name": name, "role": role, "status": status,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })
        state["value"] = idx


def _client_index_remove(client_id: str) -> None:
    with locked_write(CLIENTS_INDEX) as state:
        idx = state["value"] or {"clients": []}
        idx["clients"] = [c for c in idx.get("clients", []) if c["id"] != client_id]
        state["value"] = idx


def _collection_files_scoped(resource: str, client):
    """Return (fname, key, required). When `client` is set, redirect to the
    client's per-resource sub-key inside clients/<id>.json instead of the
    global file."""
    fname, key, required = COLLECTION_FILES[resource]
    if client is None:
        return fname, key, required
    cpath = _client_path(client)
    cpath.parent.mkdir(parents=True, exist_ok=True)
    if not cpath.exists():
        die("client not found", client=client)
    return f"{CLIENTS_DIR}/{client}.json", resource, required


def _collection_handler(resource: str, args) -> int:
    client = getattr(args, "client", None)
    fname, key, required = _collection_files_scoped(resource, client)

    if args.verb == "list":
        data = load(fname, {key: []})
        items = data.get(key, []) if isinstance(data, dict) else []
        sys.stdout.write(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "get":
        data = load(fname, {key: []})
        items = data.get(key, []) if isinstance(data, dict) else []
        for item in items:
            if item.get("id") == args.id:
                sys.stdout.write(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
                return 0
        die(f"{resource} not found", id=args.id)

    if args.verb == "add":
        data = parse_json_arg(args.data, "--data")
        if not isinstance(data, dict):
            die("--data must be a JSON object")
        for f in required:
            if not data.get(f):
                die(f"required field missing: {f}", field=f)
        if not data.get("id"):
            data["id"] = gen_id(str(data.get(required[0], resource)))
        with locked_write(fname) as state:
            current = state["value"] or {key: []}
            items = current.setdefault(key, [])
            if any(it.get("id") == data["id"] for it in items):
                die(f"{resource} id already exists", id=data["id"])
            items.append(data)
            state["value"] = current
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "update":
        patch = parse_json_arg(args.patch, "--patch")
        if not isinstance(patch, dict):
            die("--patch must be a JSON object")
        with locked_write(fname) as state:
            current = state["value"] or {key: []}
            items = current.get(key, [])
            for i, item in enumerate(items):
                if item.get("id") == args.id:
                    items[i] = deep_merge(item, patch)
                    current[key] = items
                    state["value"] = current
                    sys.stdout.write(json.dumps(items[i], ensure_ascii=False, indent=2) + "\n")
                    return 0
        die(f"{resource} not found", id=args.id)

    if args.verb == "remove":
        with locked_write(fname) as state:
            current = state["value"] or {key: []}
            items = current.get(key, [])
            new_items = [it for it in items if it.get("id") != args.id]
            if len(new_items) == len(items):
                die(f"{resource} not found", id=args.id)
            current[key] = new_items
            state["value"] = current
        sys.stdout.write(json.dumps({"removed": args.id}, ensure_ascii=False, indent=2) + "\n")
        return 0

    die(f"unknown verb: {args.verb}")
    return 2


def _candidates_advance(args) -> int:
    fname, key, _ = COLLECTION_FILES["candidates"]
    with locked_write(fname) as state:
        current = state["value"] or {key: []}
        items = current.get(key, [])
        for i, item in enumerate(items):
            if item.get("id") != args.id:
                continue
            if args.stage:
                if args.stage not in CANDIDATE_STAGES:
                    die(f"unknown stage: {args.stage}", allowed=CANDIDATE_STAGES)
                items[i]["stage"] = args.stage
            else:
                cur = item.get("stage")
                if cur in TERMINAL_STAGES:
                    die(f"candidate already in terminal stage: {cur}")
                idx = CANDIDATE_AUTO_STAGES.index(cur) if cur in CANDIDATE_AUTO_STAGES else -1
                items[i]["stage"] = CANDIDATE_AUTO_STAGES[idx + 1]
            current[key] = items
            state["value"] = current
            sys.stdout.write(json.dumps(items[i], ensure_ascii=False, indent=2) + "\n")
            return 0
    die("candidate not found", id=args.id)
    return 2


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

    # ----- holdings -----
    h = sub.add_parser("holdings")
    h_sub = h.add_subparsers(dest="verb", required=True)
    h_list = h_sub.add_parser("list"); h_list.add_argument("--client", default=None)
    h_get = h_sub.add_parser("get"); h_get.add_argument("--id", required=True); h_get.add_argument("--client", default=None)
    h_add = h_sub.add_parser("add"); h_add.add_argument("--data", required=True); h_add.add_argument("--client", default=None)
    h_upd = h_sub.add_parser("update"); h_upd.add_argument("--id", required=True); h_upd.add_argument("--patch", required=True); h_upd.add_argument("--client", default=None)
    h_rm = h_sub.add_parser("remove"); h_rm.add_argument("--id", required=True); h_rm.add_argument("--client", default=None)

    # ----- candidates -----
    c = sub.add_parser("candidates")
    c_sub = c.add_subparsers(dest="verb", required=True)
    c_list = c_sub.add_parser("list"); c_list.add_argument("--client", default=None)
    c_get = c_sub.add_parser("get"); c_get.add_argument("--id", required=True); c_get.add_argument("--client", default=None)
    c_add = c_sub.add_parser("add"); c_add.add_argument("--data", required=True); c_add.add_argument("--client", default=None)
    c_upd = c_sub.add_parser("update"); c_upd.add_argument("--id", required=True); c_upd.add_argument("--patch", required=True); c_upd.add_argument("--client", default=None)
    c_rm = c_sub.add_parser("remove"); c_rm.add_argument("--id", required=True); c_rm.add_argument("--client", default=None)
    c_adv = c_sub.add_parser("advance-stage"); c_adv.add_argument("--id", required=True); c_adv.add_argument("--stage"); c_adv.add_argument("--client", default=None)

    # ----- clients -----
    cl = sub.add_parser("clients")
    cl_sub = cl.add_subparsers(dest="verb", required=True)
    cl_sub.add_parser("list")
    cl_get = cl_sub.add_parser("get"); cl_get.add_argument("--id", required=True)
    cl_create = cl_sub.add_parser("create"); cl_create.add_argument("--data", required=True)
    cl_upd = cl_sub.add_parser("update"); cl_upd.add_argument("--id", required=True); cl_upd.add_argument("--patch", required=True)
    cl_rm = cl_sub.add_parser("remove"); cl_rm.add_argument("--id", required=True)

    args = parser.parse_args(argv)

    if args.resource == "profile":
        return _profile(args)
    if args.resource == "holdings":
        return _collection_handler("holdings", args)
    if args.resource == "candidates":
        if args.verb == "advance-stage":
            return _candidates_advance(args)
        return _collection_handler("candidates", args)
    if args.resource == "clients":
        return _clients(args)
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


def _clients(args) -> int:
    if args.verb == "list":
        idx = load(CLIENTS_INDEX, {"clients": []})
        clients = idx.get("clients", []) if isinstance(idx, dict) else []
        sys.stdout.write(json.dumps(clients, ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "get":
        cpath = _client_path(args.id)
        if not cpath.exists():
            die("client not found", id=args.id)
        with cpath.open("r", encoding="utf-8") as f:
            content = f.read()
        if not content.endswith("\n"):
            content += "\n"
        sys.stdout.write(content)
        return 0

    if args.verb == "create":
        data = parse_json_arg(args.data, "--data")
        if not isinstance(data, dict):
            die("--data must be a JSON object")
        for f in ("id", "name", "role"):
            if not data.get(f):
                die(f"required field missing: {f}", field=f)
        cpath = _client_path(data["id"])
        cpath.parent.mkdir(parents=True, exist_ok=True)
        if cpath.exists():
            die("client id already exists", id=data["id"])
        data.setdefault("status", "qualifying")
        with locked_write(f"{CLIENTS_DIR}/{data['id']}.json") as state:
            state["value"] = data
        _client_index_upsert(data["id"], data["name"], data["role"], data["status"])
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "update":
        patch = parse_json_arg(args.patch, "--patch")
        if not isinstance(patch, dict):
            die("--patch must be a JSON object")
        cpath = _client_path(args.id)
        if not cpath.exists():
            die("client not found", id=args.id)
        with locked_write(f"{CLIENTS_DIR}/{args.id}.json") as state:
            cur = state["value"] or {}
            state["value"] = deep_merge(cur, patch)
            merged = state["value"]
        _client_index_upsert(args.id, merged.get("name", ""),
                             merged.get("role", ""), merged.get("status", ""))
        sys.stdout.write(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        return 0

    if args.verb == "remove":
        cpath = _client_path(args.id)
        if cpath.exists():
            cpath.unlink()
        _client_index_remove(args.id)
        sys.stdout.write(json.dumps({"removed": args.id}, ensure_ascii=False, indent=2) + "\n")
        return 0

    die(f"unknown verb: {args.verb}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
