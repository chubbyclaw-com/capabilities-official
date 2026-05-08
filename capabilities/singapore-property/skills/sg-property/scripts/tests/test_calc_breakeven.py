import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_breakeven.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_breakeven_2pct_growth(run_script):
    code, res, _ = _run(run_script, purchase_price=1_000_000,
                        selling_costs_pct=0.05, growth_rate_annual=0.02)
    assert res["breakeven_years"] >= 2.5
    assert res["breakeven_years"] <= 3


def test_breakeven_zero_growth(run_script):
    code, res, _ = _run(run_script, purchase_price=1_000_000,
                        selling_costs_pct=0.05, growth_rate_annual=0)
    assert res["breakeven_years"] is None
    assert "never" in res.get("reason", "").lower() or "no growth" in res.get("reason", "").lower()


def test_breakeven_missing(run_script):
    code, _, err = run_script("calc_breakeven.py", stdin=json.dumps({}))
    assert code == 2
    for f in ("purchase_price", "selling_costs_pct", "growth_rate_annual"):
        assert f in err
