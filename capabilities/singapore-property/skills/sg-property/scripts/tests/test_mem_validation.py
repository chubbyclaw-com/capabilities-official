import json


def test_unknown_field_warns_but_writes(run_script):
    code, out, err = run_script(
        "mem.py", "profile", "set",
        "--patch", json.dumps({"identity": {"favorite_color": "blue"}}),
    )
    assert code == 0
    assert "favorite_color" in err  # warning on stderr
    assert "warning" in err.lower()
    profile = json.loads(out)
    assert profile["identity"]["favorite_color"] == "blue"  # still written


def test_known_field_wrong_type_rejected(run_script):
    code, _, err = run_script(
        "mem.py", "profile", "set",
        "--patch", json.dumps({"finance": {"monthly_income_sgd": "lots"}}),
    )
    assert code == 2
    assert "monthly_income_sgd" in err
    assert "number" in err.lower() or "type" in err.lower() or "int" in err.lower() or "float" in err.lower()


def test_holdings_known_type_check(run_script):
    code, _, err = run_script(
        "mem.py", "holdings", "add",
        "--data", json.dumps({"address": "X", "purchase_price_sgd": "two million"}),
    )
    assert code == 2
    assert "purchase_price_sgd" in err
