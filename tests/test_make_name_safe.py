import os
from pathlib import Path

import pytest
from flywheel_gear_toolkit.utils.make_file_name_safe import make_file_name_safe


@pytest.mark.parametrize(
    "input_str, rplc_str, expected_str",
    [
        ("simple", None, "simple"),
        ("a space", None, "aspace"),
        ("??a[b,c", None, "abc"),
        ("??a[b,c", "_", "_a_b_c"),
        ("butter(fly", 91, "butterfly"),
        (".period", None, "period"),
    ],
)
def test_make_file_name_safe(input_str, rplc_str, expected_str):
    if rplc_str:
        safe_str = make_file_name_safe(input_str, rplc_str)
    else:
        # default behavior
        safe_str = make_file_name_safe(input_str)
    assert safe_str == expected_str
