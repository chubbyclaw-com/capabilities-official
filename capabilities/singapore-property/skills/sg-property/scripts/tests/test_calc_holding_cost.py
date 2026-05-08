import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_holding_cost.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_holding_cost_basic(run_script):
    code, res, _ = _run(run_script, mortgage_monthly=4000, maintenance_monthly=400,
                        property_tax_annual=3000, income_tax_annual=0)
    assert res["monthly_cost"] == 4650
    assert res["annual_cost"] == 55800


def test_holding_cost_with_income_tax(run_script):
    code, res, _ = _run(run_script, mortgage_monthly=0, maintenance_monthly=400,
                        property_tax_annual=3000, income_tax_annual=6000)
    assert res["monthly_cost"] == 1150


def test_holding_cost_missing_inputs(run_script):
    code, _, err = run_script("calc_holding_cost.py", stdin=json.dumps({}))
    assert code == 2
    for f in ("mortgage_monthly", "maintenance_monthly", "property_tax_annual"):
        assert f in err
