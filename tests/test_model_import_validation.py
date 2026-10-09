import pytest

from nano.model_manager import validate_import_request


def test_validates_default_model_import():
    assert validate_import_request(
        "litert-community/Qwen3-1.7B",
        "Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm",
        "qwen3-1.7b",
    ) == (
        "litert-community/Qwen3-1.7B",
        "Qwen3-1.7B_dynamic_wi4b32_afp32.litertlm",
        "qwen3-1.7b",
    )


@pytest.mark.parametrize(
    "repo,filename,model_id",
    [
        ("https://example.com/model", "model.litertlm", "qwen"),
        ("owner/repo", "../model.litertlm", "qwen"),
        ("owner/repo", "model.bin", "qwen"),
        ("owner/repo", "model.litertlm", "../../other"),
        ("owner/repo/extra", "model.litertlm", "qwen"),
    ],
)
def test_rejects_invalid_model_import_values(repo, filename, model_id):
    with pytest.raises(ValueError):
        validate_import_request(repo, filename, model_id)
