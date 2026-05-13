import json

CLIENT = {
    "id": "tan-001",
    "name": "Mr Tan",
    "role": "buyer",
    "status": "qualifying",
}


def test_clients_create_then_list(run_script):
    code, _, err = run_script("mem.py", "clients", "create", "--data", json.dumps(CLIENT))
    assert code == 0, err

    code, out, _ = run_script("mem.py", "clients", "list")
    listing = json.loads(out)
    assert len(listing) == 1
    assert listing[0]["id"] == "tan-001"
    assert listing[0]["name"] == "Mr Tan"
    assert "updated_at" in listing[0]


def test_clients_get_returns_full_record(run_script):
    run_script("mem.py", "clients", "create", "--data", json.dumps(CLIENT))
    code, out, _ = run_script("mem.py", "clients", "get", "--id", "tan-001")
    rec = json.loads(out)
    assert rec["id"] == "tan-001"
    assert rec["role"] == "buyer"


def test_clients_update_merges(run_script):
    run_script("mem.py", "clients", "create", "--data", json.dumps(CLIENT))
    code, out, _ = run_script(
        "mem.py", "clients", "update", "--id", "tan-001",
        "--patch", json.dumps({"status": "viewing"}),
    )
    assert code == 0
    assert json.loads(out)["status"] == "viewing"


def test_clients_remove(run_script):
    run_script("mem.py", "clients", "create", "--data", json.dumps(CLIENT))
    code, _, _ = run_script("mem.py", "clients", "remove", "--id", "tan-001")
    assert code == 0
    code, out, _ = run_script("mem.py", "clients", "list")
    assert json.loads(out) == []


def test_holdings_under_client_scope(run_script):
    run_script("mem.py", "clients", "create", "--data", json.dumps(CLIENT))
    code, _, err = run_script(
        "mem.py", "holdings", "add", "--client", "tan-001",
        "--data", json.dumps({"address": "X #01-01", "type": "private"}),
    )
    assert code == 0, err

    code, out, _ = run_script("mem.py", "holdings", "list", "--client", "tan-001")
    listing = json.loads(out)
    assert len(listing) == 1

    # global holdings still empty
    code, out, _ = run_script("mem.py", "holdings", "list")
    assert json.loads(out) == []
