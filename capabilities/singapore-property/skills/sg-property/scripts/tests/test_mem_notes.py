import json


def test_notes_append_to_profile(run_script):
    code, _, err = run_script("mem.py", "notes", "append",
                              "--target", "profile", "--text", "wants ground floor unit")
    assert code == 0, err
    code, out, _ = run_script("mem.py", "profile", "get")
    assert "wants ground floor unit" in json.loads(out)["notes"]


def test_notes_append_to_holding(run_script):
    run_script("mem.py", "holdings", "add", "--data", json.dumps({"id": "x", "address": "A"}))
    code, _, err = run_script("mem.py", "notes", "append", "--target", "holdings",
                              "--id", "x", "--text", "tenant gives notice")
    assert code == 0, err
    code, out, _ = run_script("mem.py", "holdings", "get", "--id", "x")
    assert "tenant gives notice" in json.loads(out)["notes"]


def test_notes_append_creates_profile_notes_if_missing(run_script):
    run_script("mem.py", "notes", "append", "--target", "profile", "--text", "first note")
    run_script("mem.py", "notes", "append", "--target", "profile", "--text", "second note")
    code, out, _ = run_script("mem.py", "profile", "get")
    notes = json.loads(out)["notes"]
    assert "first note" in notes
    assert "second note" in notes


def test_notes_to_client(run_script):
    run_script("mem.py", "clients", "create",
               "--data", json.dumps({"id": "tan", "name": "Mr Tan", "role": "buyer"}))
    code, _, err = run_script("mem.py", "notes", "append", "--target", "clients",
                              "--client", "tan", "--text", "prefers freehold")
    assert code == 0, err
    code, out, _ = run_script("mem.py", "clients", "get", "--id", "tan")
    assert "prefers freehold" in json.loads(out)["notes"]
