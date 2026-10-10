from nano.settings import BOOL_KEYS, DEFAULTS, _normalize


def test_default_model_download_is_enabled_and_boolean_setting():
    assert DEFAULTS["auto_download_model"] == "true"
    assert "auto_download_model" in BOOL_KEYS
    assert _normalize("auto_download_model", "false") == "false"
    assert _normalize("auto_download_model", "yes") == "true"
