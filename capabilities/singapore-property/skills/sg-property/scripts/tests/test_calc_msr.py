import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_msr.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_msr_30pct_cap(run_script):
    code, res, _ = _run(run_script, monthly_income=10000, loan_tenure=25)
    assert res["max_monthly_payment"] == 3000
    assert res["max_loan"] > 0


def test_msr_zero_income(run_script):
    code, res, _ = _run(run_script, monthly_income=0, loan_tenure=25)
    assert res["max_monthly_payment"] == 0
    assert res["max_loan"] == 0


def test_msr_custom_stress(run_script):
    code, res, _ = _run(run_script, monthly_income=10000, loan_tenure=25, stress_rate=5.0)
    code2, res2, _ = _run(run_script, monthly_income=10000, loan_tenure=25, stress_rate=4.0)
    assert res2["max_loan"] > res["max_loan"]


def test_msr_missing_input(run_script):
    code, _, err = run_script("calc_msr.py", stdin=json.dumps({"monthly_income": 5000}))
    assert code == 2
    assert "loan_tenure" in err
