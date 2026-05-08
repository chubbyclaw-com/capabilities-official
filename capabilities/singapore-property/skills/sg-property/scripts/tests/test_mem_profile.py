import json


def test_profile_set_then_get_roundtrips(run_script):
    code, _, err = run_script(
        "mem.py", "profile", "set",
        "--patch", json.dumps({"finance": {"monthly_income_sgd": 18000}}),
    )
    assert code == 0, err

    code, out, _ = run_script("mem.py", "profile", "get")
    assert code == 0
    assert json.loads(out) == {"finance": {"monthly_income_sgd": 18000}}


def test_profile_set_deep_merges(run_script):
    run_script("mem.py", "profile", "set",
               "--patch", json.dumps({"finance": {"monthly_income_sgd": 18000}}))
    run_script("mem.py", "profile", "set",
               "--patch", json.dumps({"finance": {"cpf_oa_sgd": 200000}}))

    code, out, _ = run_script("mem.py", "profile", "get")
    assert code == 0
    profile = json.loads(out)
    assert profile["finance"] == {"monthly_income_sgd": 18000, "cpf_oa_sgd": 200000}


def test_profile_clear_removes_field(run_script):
    run_script("mem.py", "profile", "set",
               "--patch", json.dumps({"finance": {"monthly_income_sgd": 18000, "cpf_oa_sgd": 200000}}))
    code, _, _ = run_script("mem.py", "profile", "clear", "--field", "finance.cpf_oa_sgd")
    assert code == 0

    code, out, _ = run_script("mem.py", "profile", "get")
    profile = json.loads(out)
    assert profile["finance"] == {"monthly_income_sgd": 18000}


def test_profile_clear_unknown_field_noop(run_script):
    code, _, _ = run_script("mem.py", "profile", "clear", "--field", "nope.nada")
    assert code == 0


def test_profile_set_requires_object(run_script):
    code, _, err = run_script("mem.py", "profile", "set", "--patch", json.dumps([1, 2, 3]))
    assert code == 2
    assert "object" in err.lower()
