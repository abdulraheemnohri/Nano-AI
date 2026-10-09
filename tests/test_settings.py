import pytest

from nano.settings import DEFAULTS, _normalize, schema


def test_all_settings_have_descriptions_and_defaults():
    items = schema()
    assert {item["key"] for item in items} == set(DEFAULTS)
    assert all(item["description"] and item["default"] == DEFAULTS[item["key"]] for item in items)


@pytest.mark.parametrize("key,value", [
    ("theme", "neon"),
    ("language", "../../tmp"),
    ("temperature", "nan"),
    ("temperature", "2.1"),
    ("max_tokens", "5000"),
    ("max_history", "129"),
    ("memory_limit", "101"),
    ("knowledge_limit", "5001"),
    ("voice_enabled", "sometimes"),
    ("unknown", "value"),
])
def test_invalid_setting_values_are_rejected(key, value):
    with pytest.raises(ValueError):
        _normalize(key, value)


def test_settings_normalize_valid_boolean_language_and_ranges():
    assert _normalize("voice_enabled", "YES") == "true"
    assert _normalize("language", "Urdu") == "Urdu"
    assert _normalize("theme", "system") == "system"
    assert _normalize("knowledge_limit", "5000") == "5000"
