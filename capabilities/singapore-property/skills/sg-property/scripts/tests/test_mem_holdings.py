import json


SAMPLE = {
    "address": "Marine Blue #18-05",
    "type": "private",
    "purchase_date": "2019-08",
    "purchase_price_sgd": 1380000,
}


def test_holdings_list_empty(run_script):
    code, out, _ = run_script("mem.py", "holdings", "list")
    assert code == 0
    assert json.loads(out) == []


def test_holdings_add_then_list(run_script):
    code, out, err = run_script("mem.py", "holdings", "add", "--data", json.dumps(SAMPLE))
    assert code == 0, err
    added = json.loads(out)
    assert added["address"] == SAMPLE["address"]
    assert added["id"]  # auto-generated

    code, out, _ = run_script("mem.py", "holdings", "list")
    listing = json.loads(out)
    assert len(listing) == 1
    assert listing[0]["id"] == added["id"]


def test_holdings_add_with_explicit_id(run_script):
    code, out, _ = run_script(
        "mem.py", "holdings", "add",
        "--data", json.dumps({**SAMPLE, "id": "my-marine-blue"}),
    )
    assert code == 0
    assert json.loads(out)["id"] == "my-marine-blue"


def test_holdings_add_duplicate_id_rejected(run_script):
    payload = json.dumps({**SAMPLE, "id": "x"})
    run_script("mem.py", "holdings", "add", "--data", payload)
    code, _, err = run_script("mem.py", "holdings", "add", "--data", payload)
    assert code == 2
    assert "already exists" in err.lower()


def test_holdings_get_by_id(run_script):
    run_script("mem.py", "holdings", "add",
               "--data", json.dumps({**SAMPLE, "id": "x"}))
    code, out, _ = run_script("mem.py", "holdings", "get", "--id", "x")
    assert code == 0
    assert json.loads(out)["address"] == SAMPLE["address"]


def test_holdings_get_missing(run_script):
    code, _, err = run_script("mem.py", "holdings", "get", "--id", "nope")
    assert code == 2
    assert "not found" in err.lower()


def test_holdings_update_patches_in_place(run_script):
    run_script("mem.py", "holdings", "add", "--data", json.dumps({**SAMPLE, "id": "x"}))
    code, out, _ = run_script(
        "mem.py", "holdings", "update", "--id", "x",
        "--patch", json.dumps({"current_loan_sgd": 720000}),
    )
    assert code == 0
    rec = json.loads(out)
    assert rec["current_loan_sgd"] == 720000
    assert rec["address"] == SAMPLE["address"]


def test_holdings_remove(run_script):
    run_script("mem.py", "holdings", "add", "--data", json.dumps({**SAMPLE, "id": "x"}))
    code, _, _ = run_script("mem.py", "holdings", "remove", "--id", "x")
    assert code == 0

    code, out, _ = run_script("mem.py", "holdings", "list")
    assert json.loads(out) == []


def test_holdings_add_requires_address(run_script):
    code, _, err = run_script("mem.py", "holdings", "add", "--data", json.dumps({"type": "private"}))
    assert code == 2
    assert "address" in err.lower()
