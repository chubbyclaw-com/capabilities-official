import json

SAMPLE = {
    "project_name": "Stirling Residences",
    "address": "Stirling Rd",
    "asking_price_sgd": 2350000,
}


def test_candidates_add_get_list(run_script):
    code, out, err = run_script("mem.py", "candidates", "add", "--data", json.dumps(SAMPLE))
    assert code == 0, err
    cid = json.loads(out)["id"]

    code, out, _ = run_script("mem.py", "candidates", "get", "--id", cid)
    assert json.loads(out)["project_name"] == "Stirling Residences"


def test_candidates_advance_stage_progression(run_script):
    code, out, _ = run_script("mem.py", "candidates", "add", "--data", json.dumps(SAMPLE))
    cid = json.loads(out)["id"]

    code, out, _ = run_script("mem.py", "candidates", "advance-stage", "--id", cid)
    assert code == 0
    assert json.loads(out)["stage"] == "shortlist"

    for expected in ("viewing_scheduled", "viewed", "offered", "closed"):
        code, out, _ = run_script("mem.py", "candidates", "advance-stage", "--id", cid)
        assert json.loads(out)["stage"] == expected


def test_candidates_advance_stage_explicit_target(run_script):
    code, out, _ = run_script("mem.py", "candidates", "add", "--data", json.dumps(SAMPLE))
    cid = json.loads(out)["id"]
    code, out, _ = run_script("mem.py", "candidates", "advance-stage", "--id", cid, "--stage", "declined")
    assert code == 0
    assert json.loads(out)["stage"] == "declined"


def test_candidates_advance_stage_terminal_rejected(run_script):
    code, out, _ = run_script("mem.py", "candidates", "add", "--data", json.dumps(SAMPLE))
    cid = json.loads(out)["id"]
    for _ in range(5):
        run_script("mem.py", "candidates", "advance-stage", "--id", cid)
    code, _, err = run_script("mem.py", "candidates", "advance-stage", "--id", cid)
    assert code == 2
    assert "terminal" in err.lower() or "closed" in err.lower()
