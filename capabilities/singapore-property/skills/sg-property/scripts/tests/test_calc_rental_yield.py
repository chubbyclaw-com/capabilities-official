import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_rental_yield.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_yield_basic(run_script):
    code, res, _ = _run(run_script, annual_rent=72000, purchase_price=1_500_000,
                        maintenance_annual=4800, property_tax_annual=4000)
    assert res["gross_yield"] == 0.048
    assert round(res["net_yield"], 4) == 0.0421


def test_yield_zero_price_error(run_script):
    code, _, err = run_script("calc_rental_yield.py",
                              stdin=json.dumps({"annual_rent": 60000, "purchase_price": 0}))
    assert code == 2
    assert "purchase_price" in err


def test_yield_missing_inputs(run_script):
    code, _, err = run_script("calc_rental_yield.py",
                              stdin=json.dumps({"annual_rent": 60000}))
    assert code == 2
    assert "purchase_price" in err
