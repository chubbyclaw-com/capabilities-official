import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_tdsr.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_basic_no_existing_debt(run_script):
    code, res, _ = _run(run_script, monthly_income=18000, monthly_debt=0, loan_tenure=30)
    assert code == 0
    assert res["max_monthly_payment"] == 9900
    assert 2_000_000 < res["max_loan"] < 2_150_000


def test_existing_debt_reduces(run_script):
    code, res, _ = _run(run_script, monthly_income=18000, monthly_debt=2500, loan_tenure=30)
    assert res["max_monthly_payment"] == 7400


def test_zero_capacity(run_script):
    code, res, _ = _run(run_script, monthly_income=10000, monthly_debt=5500, loan_tenure=25)
    assert res["max_monthly_payment"] == 0
    assert res["max_loan"] == 0


def test_custom_stress_rate(run_script):
    code, res, _ = _run(run_script, monthly_income=18000, monthly_debt=0,
                        loan_tenure=30, stress_rate=5.0)
    assert res["max_loan"] < 2_000_000


def test_missing_inputs(run_script):
    code, _, err = run_script("calc_tdsr.py", stdin=json.dumps({"monthly_income": 1}))
    assert code == 2
    for f in ("monthly_debt", "loan_tenure"):
        assert f in err
