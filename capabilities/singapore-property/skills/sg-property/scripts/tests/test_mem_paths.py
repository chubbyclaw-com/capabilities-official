import json
import os


def test_help_lists_resources(run_script):
    code, out, err = run_script("mem.py", "--help")
    assert code == 0
    for word in ("profile", "holdings", "candidates", "clients", "notes"):
        assert word in out


def test_unknown_resource_exits_2(run_script):
    code, out, err = run_script("mem.py", "wat", "get")
    assert code == 2


def test_profile_get_on_missing_returns_empty_object(run_script, sgprop_home):
    code, out, err = run_script("mem.py", "profile", "get")
    assert code == 0, err
    assert json.loads(out) == {}
    # Directory created with 0700
    assert sgprop_home.is_dir()
    assert (os.stat(sgprop_home).st_mode & 0o777) == 0o700
