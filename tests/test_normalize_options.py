from preflight import _normalize_options


def test_json_array_string():
    assert _normalize_options('["Yes", "No", "Maybe"]') == ["Yes", "No", "Maybe"]


def test_comma_separated_string():
    assert _normalize_options("Yes, No, Maybe") == ["Yes", "No", "Maybe"]


def test_already_a_list():
    assert _normalize_options(["Yes", "No"]) == ["Yes", "No"]


def test_strips_and_drops_empties():
    assert _normalize_options('["  Yes  ", "", "  ", "No"]') == ["Yes", "No"]


def test_dedupes_preserving_order():
    assert _normalize_options("B, A, B, C, A") == ["B", "A", "C"]


def test_truncates_long_options_to_80_chars():
    long = "x" * 100
    result = _normalize_options([long, "short"])
    assert result[0] == "x" * 80
    assert result[1] == "short"


def test_caps_at_max_options():
    opts = [f"opt{i}" for i in range(10)]
    assert _normalize_options(opts, max_options=6) == opts[:6]


def test_json_garbage_falls_back_to_comma_split():
    assert _normalize_options('{"not": "a list"') == ['{"not": "a list"']


def test_json_non_list_falls_back_to_comma_split():
    # valid JSON but not a list: treat the raw string as comma-separated
    assert _normalize_options('"just a string"') == ['"just a string"']


def test_non_string_list_items_coerced():
    assert _normalize_options([1, 2, None, "three"]) == ["1", "2", "three"]
