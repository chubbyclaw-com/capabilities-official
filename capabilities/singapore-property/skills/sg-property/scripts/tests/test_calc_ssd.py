import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_ssd.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_held_under_1y_12pct(run_script):
    code, res, _ = _run(run_script, purchase_date="2025-06-01",
                        sale_date="2026-04-01", sale_price=1_000_000)
    assert res["applies"] is True
    assert res["rate"] == 0.12
    assert res["amount"] == 120_000


def test_held_1_to_2y_8pct(run_script):
    code, res, _ = _run(run_script, purchase_date="2024-06-01",
                        sale_date="2026-04-01", sale_price=1_000_000)
    assert res["rate"] == 0.08
    assert res["amount"] == 80_000


def test_held_2_to_3y_4pct(run_script):
    code, res, _ = _run(run_script, purchase_date="2023-06-01",
                        sale_date="2026-04-01", sale_price=1_000_000)
    assert res["rate"] == 0.04
    assert res["amount"] == 40_000


def test_held_3y_plus_no_ssd(run_script):
    code, res, _ = _run(run_script, purchase_date="2022-01-01",
                        sale_date="2026-05-01", sale_price=1_000_000)
    assert res["applies"] is False
    assert res["amount"] == 0
    assert "no ssd" in res["reason"].lower() or "more than 3" in res["reason"].lower()


def test_ssd_invalid_dates(run_script):
    code, _, err = run_script("calc_ssd.py",
                              stdin=json.dumps({"purchase_date": "2024-13-99",
                                                "sale_date": "2026-01-01",
                                                "sale_price": 1_000_000}))
    assert code == 2
    assert "purchase_date" in err
