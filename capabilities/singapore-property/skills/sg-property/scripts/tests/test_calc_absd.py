import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_absd.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_sc_first_property_zero(run_script):
    code, res, _ = _run(run_script, nationality="SC", marital_status="single",
                        owned_count=0, purchase_price=1_000_000)
    assert code == 0
    assert res["rate"] == 0.0
    assert res["amount"] == 0


def test_sc_second_property_20pct(run_script):
    code, res, _ = _run(run_script, nationality="SC", marital_status="single",
                        owned_count=1, purchase_price=1_000_000)
    assert res["rate"] == 0.20
    assert res["amount"] == 200_000


def test_sc_third_property_30pct(run_script):
    code, res, _ = _run(run_script, nationality="SC", marital_status="single",
                        owned_count=2, purchase_price=1_000_000)
    assert res["rate"] == 0.30
    assert res["amount"] == 300_000


def test_pr_first_property_5pct(run_script):
    code, res, _ = _run(run_script, nationality="PR", marital_status="single",
                        owned_count=0, purchase_price=1_000_000)
    assert res["rate"] == 0.05
    assert res["amount"] == 50_000


def test_pr_second_property_30pct(run_script):
    code, res, _ = _run(run_script, nationality="PR", marital_status="single",
                        owned_count=1, purchase_price=1_000_000)
    assert res["rate"] == 0.30
    assert res["amount"] == 300_000


def test_foreigner_60pct(run_script):
    code, res, _ = _run(run_script, nationality="Foreign", marital_status="single",
                        owned_count=0, purchase_price=1_000_000)
    assert res["rate"] == 0.60
    assert res["amount"] == 600_000


def test_fta_treated_as_sc(run_script):
    code, res, _ = _run(run_script, nationality="FTA", marital_status="single",
                        owned_count=0, purchase_price=1_000_000)
    assert res["rate"] == 0.0
    assert res["fta_exempt"] is True


def test_mixed_couple_uses_higher_party(run_script):
    code, res, _ = _run(run_script, nationality="SC", marital_status="married",
                        spouse_nationality="Foreign", owned_count=0,
                        purchase_price=1_000_000)
    assert res["rate"] == 0.60
    assert "spouse" in (res.get("notes", "") + json.dumps(res.get("breakdown", []))).lower()


def test_sc_couple_first_refund_eligible(run_script):
    code, res, _ = _run(run_script, nationality="SC", marital_status="married",
                        spouse_nationality="SC", owned_count=1,
                        purchase_price=1_000_000)
    assert res["refund_eligible"] is True


def test_absd_missing_required(run_script):
    code, _, err = run_script("calc_absd.py", stdin=json.dumps({"nationality": "SC"}))
    assert code == 2
    for f in ("owned_count", "purchase_price"):
        assert f in err
