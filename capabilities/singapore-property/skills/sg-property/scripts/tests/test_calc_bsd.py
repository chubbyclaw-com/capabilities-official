import json


def _run(run_script, **payload):
    code, out, err = run_script("calc_bsd.py", stdin=json.dumps(payload))
    return code, json.loads(out) if out else None, err


def test_bsd_under_180k(run_script):
    code, res, _ = _run(run_script, purchase_price=150_000)
    assert code == 0
    assert res["amount"] == 1500  # 1% of 150k


def test_bsd_180k_to_360k(run_script):
    code, res, _ = _run(run_script, purchase_price=300_000)
    assert code == 0
    # 1% × 180k + 2% × 120k = 1800 + 2400 = 4200
    assert res["amount"] == 4200


def test_bsd_residential_1m(run_script):
    code, res, _ = _run(run_script, purchase_price=1_000_000)
    # 1%×180k + 2%×180k + 3%×640k = 1800 + 3600 + 19200 = 24600
    assert res["amount"] == 24600


def test_bsd_residential_2m(run_script):
    code, res, _ = _run(run_script, purchase_price=2_000_000)
    # 1%×180k + 2%×180k + 3%×640k + 4%×500k + 5%×500k = 1800+3600+19200+20000+25000 = 69600
    assert res["amount"] == 69600


def test_bsd_residential_4m(run_script):
    code, res, _ = _run(run_script, purchase_price=4_000_000)
    # 1%×180k + 2%×180k + 3%×640k + 4%×500k + 5%×1.5m + 6%×1m = 1800+3600+19200+20000+75000+60000 = 179600
    assert res["amount"] == 179600


def test_bsd_missing_input(run_script):
    code, _, err = run_script("calc_bsd.py", stdin=json.dumps({}))
    assert code == 2
    assert "purchase_price" in err
