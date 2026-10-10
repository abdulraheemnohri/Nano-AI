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
    ("autonomous_talk_interval_minutes", "5"),
    ("background_interval_minutes", "0"),
    ("speech_rate", "2.1"),
    ("speech_volume", "-0.1"),
    ("talk_style", "rude"),
    ("autonomous_talk_interval_minutes", "1441"),
    ("autonomous_talk_prompt", ""),
    ("autonomous_talk_prompt", "x" * 1001),
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
    assert _normalize("autonomous_talk_interval_minutes", "10") == "10"
    assert _normalize("autonomous_talk_enabled", "true") == "true"
    assert _normalize("autonomous_talk_prompt", "Say hello briefly.") == "Say hello briefly."



def test_background_recovery_and_talking_settings_are_typed_and_bounded():
    assert _normalize("background_self_check_enabled", "YES") == "true"
    assert _normalize("auto_error_resolver_enabled", "off") == "false"
    assert _normalize("background_interval_minutes", "1") == "1"
    assert _normalize("talk_style", "technical") == "technical"
    assert _normalize("talk_reply_length", "2000") == "2000"
    assert _normalize("speech_rate", "1.5") == "1.5"
    assert _normalize("speech_volume", "0.5") == "0.5"
    entries = {item["key"]: item for item in schema()}
    assert entries["talk_style"]["choices"] == ["concise", "balanced", "detailed", "warm", "technical"]
    assert entries["speech_rate"]["minimum"] == 0.5
